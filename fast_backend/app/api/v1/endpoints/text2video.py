from typing import Optional, List

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Request, Query
from pydantic import BaseModel, Field

from sqlalchemy.orm import Session

from ....api.deps import get_db, get_current_user_optional
from ....services.video_service import VideoGenerationService
from ....services.file_service import FileService
from ....services.llm_service import LLMService
from ....services.preview_qa_service import PreviewQAService
from ....services.retry_policy import encode_preview_qa_error
from ....models.video import VideoGenerationResponse, VideoQuality, VideoFormat
from ....models.user import User

router = APIRouter()


def _preview_retry_error(preview_report: dict, attempt: int) -> str:
    """Build parseable retry feedback from preview QA aggregate issue codes."""
    summary = preview_report.get("summary", {})
    aggregate_issues = summary.get("aggregate_issues", [])
    issue_codes = [str(issue.get("code", "")).strip() for issue in aggregate_issues]
    issue_codes = [code for code in issue_codes if code]
    issue_frames = {
        str(issue.get("code", "")): int(issue.get("frame_count", 0))
        for issue in aggregate_issues
        if issue.get("code")
    }
    return encode_preview_qa_error(
        attempt=attempt,
        issue_codes=issue_codes,
        issue_frames=issue_frames,
    )


class AutoModeConfig(BaseModel):
    """Configuration for auto mode video generation."""
    max_total_attempts: int = Field(default=15, ge=1, le=50, description="Maximum total attempts across all phases")
    max_llm_attempts_per_phase: int = Field(default=3, ge=1, le=10, description="Maximum LLM attempts per phase")
    enable_prompt_rewriting: bool = Field(default=True, description="Enable prompt rewriting phase")
    enable_prompt_simplification: bool = Field(default=True, description="Enable prompt simplification phase")
    enable_gemini_fallback: bool = Field(default=True, description="Enable Gemini model fallback")
    enable_video_error_feedback: bool = Field(default=True, description="Enable video error feedback for retries")
    enable_preview_qa: bool = Field(default=True, description="Render low-quality preview and run frame-level heuristic QA before final render")
    preferred_models: List[str] = Field(default=["gemma-3-27b-it", "gemini-3-flash-preview", "gemini-3.1-pro-preview", "gemini-2.5-flash"], 
                                       description="Preferred models in order of preference")
    custom_prompt_modifiers: List[str] = Field(default=[], description="Custom prompt modifiers to apply")


@router.post("/", response_model=VideoGenerationResponse, status_code=201)
async def generate_video_from_text(
    *,
    prompt: str = Query(..., description="Natural language description of the desired video"),
    model: Optional[str] = Query(None, description="LLM model identifier (e.g., 'gpt-4o', 'gemini-2.5-flash')"),
    quality: VideoQuality = Query(VideoQuality.LOW_QUALITY, description="Video quality"),
    format: VideoFormat = Query(VideoFormat.MP4, description="Output video format"),
    background_tasks: BackgroundTasks,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional),
):
    """High-level pipeline: prompt -> LLM -> Manim code -> video generation.

    The endpoint returns immediately with a record representing the video generation request. Actual rendering happens in the background.
    """
    llm_service = LLMService()

    retries = 3
    last_error: Optional[str] = None
    code: Optional[str] = None

    for attempt in range(retries):
        # Step 1: call LLM
        augmented_prompt = prompt
        if last_error:
            augmented_prompt += f"\nPrevious error: {last_error}. Please correct the Manim code and try again."
        code = await llm_service.generate_manim_code(augmented_prompt, model=model)

        if not code or "class" not in code:
            last_error = "LLM did not return valid Manim code"
            continue
        validation_result = await llm_service._validate_code_compilation(code)
        if not validation_result.get("success", False):
            last_error = validation_result.get("error")
            continue

        # Attempt dry run via VideoGenerationService (will render in background)
        file_service = FileService()
        video_service = VideoGenerationService(db, file_service)
        try:
            video_gen = await video_service.create_video_generation(
                title=prompt[:100],
                script_content=code,
                scene_name="GeneratedScene",
                user=current_user,
                description="Generated via AI prompt",
                quality=quality,
                format=format,
                output_name="ai_generated_video",
                tags=["ai", "auto"],
                video_metadata={
                    "model": model or "gemini-2.5-flash",
                    "validation_report": validation_result.get("report"),
                },
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
            )
        except Exception as exc:
            last_error = str(exc)
            continue

        # Kick off rendering
        background_tasks.add_task(video_service.start_video_generation, video_gen.id)
        return VideoGenerationResponse.from_orm(video_gen)

    raise HTTPException(status_code=400, detail=f"Failed to generate video from prompt after {retries} attempts. Last error: {last_error}")


@router.post("/auto", response_model=VideoGenerationResponse, status_code=201)
async def generate_video_auto_mode(
    *,
    prompt: str = Query(..., description="Natural language description of the desired video"),
    quality: VideoQuality = Query(VideoQuality.LOW_QUALITY, description="Video quality"),
    format: VideoFormat = Query(VideoFormat.MP4, description="Output video format"),
    auto_config: Optional[AutoModeConfig] = None,
    background_tasks: BackgroundTasks,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional),
):
    """Auto mode with full pipeline retry and video validation.

    This endpoint uses the sophisticated auto mode that:
    1. Tries Gemma with error correction (3 attempts)
    2. Rewrites prompt and tries again (3 attempts)
    3. Simplifies prompt and tries again (3 attempts)
    4. Falls back to Gemini Flash Lite (2 attempts)
    5. Falls back to Gemini Flash (1 attempt)
    6. Final attempt with simplified prompt + Gemini Flash

    If video generation fails, it feeds the errors back to improve the next attempt.
    
    Customization is available through the auto_config parameter.
    """
    # Use default config if none provided
    if auto_config is None:
        auto_config = AutoModeConfig()
    
    llm_service = LLMService()
    file_service = FileService()
    video_service = VideoGenerationService(db, file_service)

    video_errors = []
    max_total_attempts = auto_config.max_total_attempts
    preview_qa_service = (
        PreviewQAService(manim_generator=video_service.manim_generator)
        if auto_config.enable_preview_qa
        else None
    )

    for overall_attempt in range(max_total_attempts):
        try:
            # Generate code using auto mode with video error feedback
            code = await llm_service.generate_manim_code_with_video_validation(
                prompt=prompt, 
                model="auto",
                video_errors=video_errors if auto_config.enable_video_error_feedback else None,
                auto_config=auto_config
            )

            if not code or "class GeneratedScene" not in code:
                video_errors.append("LLM did not return valid GeneratedScene class")
                continue
            # Disallow use of asset-based classes we don't have (e.g., missing SVG files)
            if "SVGMobject" in code or "ImageMobject" in code:
                video_errors.append("Usage of SVGMobject or ImageMobject is not allowed without assets")
                continue
            # Actual compilation check: ensure generated code compiles and is structurally valid
            compilation_result = await llm_service._validate_code_compilation(code)
            if not compilation_result.get("success", False):
                video_errors.append(f"Compilation error: {compilation_result.get('error')}")
                continue
            # Convert code for Manim v0.19+ and re-validate
            from ....services.manim_code_converter import convert_manim_code
            converted_script = convert_manim_code(code)
            converted_validation = await llm_service._validate_code_compilation(converted_script)
            if not converted_validation.get("success", False):
                video_errors.append(f"Converted code error: {converted_validation.get('error')}")
                continue
            # Use converted script for actual video generation
            code_to_use = converted_script

            quality_risks = llm_service.analyze_quality_risks(prompt=prompt, code=code_to_use)
            if quality_risks:
                video_errors.extend(quality_risks)
                continue

            preview_report = None
            if auto_config.enable_preview_qa and preview_qa_service is not None:
                preview_report = preview_qa_service.run_preview_qa(
                    script_content=code_to_use,
                    scene_name="GeneratedScene",
                )
                if not preview_report.get("ok", False):
                    video_errors.append(
                        _preview_retry_error(
                            preview_report=preview_report,
                            attempt=overall_attempt + 1,
                        )
                    )
                    continue
            
            # Create video generation request
            video_gen = await video_service.create_video_generation(
                title=prompt[:100],
                script_content=code_to_use,
                scene_name="GeneratedScene",
                user=current_user,
                description="Generated via AI auto mode",
                quality=quality,
                format=format,
                output_name="auto_generated_video",
                tags=["ai", "auto", "advanced"],
                video_metadata={
                    "model": "auto", 
                    "attempt": overall_attempt + 1,
                    "auto_config": auto_config.dict(),
                    "validation_report": converted_validation.get("report"),
                    "source_validation_report": compilation_result.get("report"),
                    "preview_qa_report": preview_report,
                },
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
            )

            # Try to generate the video synchronously to get immediate feedback
            # This is different from the background approach - we need to know if it fails
            try:
                # Run video generation synchronously to catch errors immediately
                await video_service.start_video_generation(video_gen.id)
                # Generation succeeded
                return VideoGenerationResponse.from_orm(video_gen)
            except Exception as video_error:
                # Collect the failure and retry
                err = str(video_error)
                video_errors.append(err)
                video_gen.fail(err)
                db.commit()
                # Retry if attempts remain
                if overall_attempt < max_total_attempts - 1:
                    continue
                # Exhausted all attempts -> return detailed error
                raise HTTPException(
                    status_code=500,
                    detail={
                        "message": f"Auto mode failed after {max_total_attempts} attempts.",
                        "errors": video_errors
                    }
                )
        except Exception as e:
            error_msg = str(e)
            video_errors.append(f"Generation attempt {overall_attempt + 1} failed: {error_msg}")

            if overall_attempt >= max_total_attempts - 1:
                raise HTTPException(
                    status_code=500,
                    detail=f"Auto mode failed after {max_total_attempts} attempts. Errors: {'; '.join(video_errors[-5:])}"
                )

    # Fallback - should not reach here
    raise HTTPException(status_code=500, detail="Auto mode exhausted all retry attempts")
