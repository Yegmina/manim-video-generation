from typing import Optional, Dict, Any, List
import logging
import os
import re

from ..core.config import settings
from .validation_report import ValidationReportBuilder

logger = logging.getLogger(__name__)


class LLMService:
    """Simple abstraction for calling different LLM providers.

    Currently works as a stub returning example Manim code. Extend this class
    to integrate with real providers such as Google Gemini, OpenAI, Anthropic, etc.
    """

    # Mapping of friendly model names to provider + model identifiers
    _MODEL_MAP: Dict[str, Dict[str, Any]] = {
        # provider, model name, additional kwargs if necessary
        "gemini-2.5-flash": {"provider": "google", "model": "gemini-2.5-flash"},
        "gemini-2.5-pro": {"provider": "google", "model": "gemini-2.5-pro"},
        "gemini-2.5-flash-lite": {"provider": "google", "model": "gemini-2.5-flash-lite"},
        "gemma-3-27b-it": {"provider": "google", "model": "gemma-3-27b-it"},
        "gemma-3-9b-it": {"provider": "google", "model": "gemma-3-9b-it"},
        "gpt-4o": {"provider": "openai", "model": "gpt-4o"},
        "auto": {"provider": "auto", "model": "auto"},
    }

    # Model-specific system prompts
    _SYSTEM_PROMPTS: Dict[str, str] = {
        # Gemini models - more up-to-date, need less guidance
        "gemini-2.5-flash": (
            "You are an expert Manim developer. Given a user description, "
            "return ONLY valid Python code that defines a Scene subclass named "
            "'GeneratedScene' which fulfils the request. "
            "Do not include markdown formatting, code blocks, or any explanations. "
            "Return only the raw Python code starting with 'from manim import *'."
        ),
        "gemini-2.5-pro": (
            "You are an expert Manim developer. Given a user description, "
            "return ONLY valid Python code that defines a Scene subclass named "
            "'GeneratedScene' which fulfils the request. "
            "Do not include markdown formatting, code blocks, or any explanations. "
            "Return only the raw Python code starting with 'from manim import *'."
        ),
        "gemini-2.5-flash-lite": (
            "You are an expert Manim developer. Given a user description, "
            "return ONLY valid Python code that defines a Scene subclass named "
            "'GeneratedScene' which fulfils the request. "
            "Do not include markdown formatting, code blocks, or any explanations. "
            "Return only the raw Python code starting with 'from manim import *'."
        ),
        # Gemma models - need specific API guidance for current Manim version
        "gemma-3-27b-it": (
            "You are an expert Manim developer. Given a user description, "
            "return ONLY valid Python code that defines a Scene subclass named "
            "'GeneratedScene' which fulfils the request. "
            "CRITICAL: DO NOT use any of these methods - they do NOT exist in Manim v0.19.0: "
            "- DO NOT use 'axes.add_labels()' "
            "- DO NOT use 'axes.add_coordinate_labels()' "
            "- DO NOT use 'axes.coordinate_labels' "
            "Instead, use ONLY these methods for axis labels: "
            "- Use 'axes.get_x_axis_label(\"Time (s)\")' for x-axis labels "
            "- Use 'axes.get_y_axis_label(\"Position (m)\")' for y-axis labels "
            "- Use 'Text()' for all other text, avoid 'MathTex()' if possible "
            "- Use 'Dot()' for points, 'Line()' for lines "
            "- Keep animations simple and educational "
            "- Avoid complex coordinate systems, use simple shapes and text "
            "Do not include markdown formatting, code blocks, or any explanations. "
            "Return only the raw Python code starting with 'from manim import *'."
        ),
        "gemma-3-9b-it": (
            "You are an expert Manim developer. Given a user description, "
            "return ONLY valid Python code that defines a Scene subclass named "
            "'GeneratedScene' which fulfils the request. "
            "CRITICAL: DO NOT use any of these methods - they do NOT exist in Manim v0.19.0: "
            "- DO NOT use 'axes.add_labels()' "
            "- DO NOT use 'axes.add_coordinate_labels()' "
            "- DO NOT use 'axes.coordinate_labels' "
            "Instead, use ONLY these methods for axis labels: "
            "- Use 'axes.get_x_axis_label(\"Time (s)\")' for x-axis labels "
            "- Use 'axes.get_y_axis_label(\"Position (m)\")' for y-axis labels "
            "- Use 'Text()' for all other text, avoid 'MathTex()' if possible "
            "- Use 'Dot()' for points, 'Line()' for lines "
            "- Keep animations simple and educational "
            "- Avoid complex coordinate systems, use simple shapes and text "
            "Do not include markdown formatting, code blocks, or any explanations. "
            "Return only the raw Python code starting with 'from manim import *'."
        ),
        # Default for unknown models
        "default": (
            "You are an expert Manim developer. Given a user description, "
            "return ONLY valid Python code that defines a Scene subclass named "
            "'GeneratedScene' which fulfils the request. "
            "Do not include markdown formatting, code blocks, or any explanations. "
            "Return only the raw Python code starting with 'from manim import *'."
        ),
    }

    def __init__(self):
        # Place to initialise real SDK clients (e.g., google.generativeai, openai)
        pass

    async def generate_manim_code(self, prompt: str, model: Optional[str] = None) -> str:
        """Generate Manim Python code from a natural-language prompt.

        Args:
            prompt: Natural language description of the desired video.
            model: Friendly model identifier. Defaults to ``gemini-2.5-flash``.

        Returns:
            str: Manim script content.
        """
        model = model or "gemini-2.5-flash"
        config = self._MODEL_MAP.get(model, self._MODEL_MAP["gemini-2.5-flash"])

        provider = config["provider"]
        model_name = config["model"]

        logger.info(
            f"Generating Manim code using provider={provider} model={model_name} for prompt='{prompt[:60]}…'"
        )

        # Handle auto mode with fallback chain
        if provider == "auto":
            return await self._auto_mode_generate(prompt)
        
        # Simple switch-case style routing
        if provider == "google":
            try:
                from google import genai
                from google.genai import types

                # Get API key from settings
                api_key = settings.google_api_key or os.getenv("GOOGLE_API_KEY")
                if not api_key:
                    raise ValueError("GOOGLE_API_KEY not found in environment or settings")
                
                # Create client with new API
                client = genai.Client(api_key=api_key)
                
                # Prepare the prompt
                system_prompt = self._SYSTEM_PROMPTS.get(model, self._SYSTEM_PROMPTS["default"])
                full_prompt = f"{system_prompt}\n\nUser request: {prompt}"
                
                contents = [
                    types.Content(
                        role="user",
                        parts=[
                            types.Part.from_text(text=full_prompt),
                        ],
                    ),
                ]
                
                # Generate content
                response = client.models.generate_content(
                    model=model_name,
                    contents=contents,
                )
                
                # Extract the generated code
                code = response.text.strip()
                
                # Remove markdown code blocks if present
                if code.startswith("```python"):
                    code = code[9:]  # Remove ```python
                if code.startswith("```"):
                    code = code[3:]   # Remove ```
                if code.endswith("```"):
                    code = code[:-3]  # Remove trailing ```
                
                code = code.strip()
                
                # Basic guard – ensure contains a Scene subclass
                if "class GeneratedScene" not in code:
                    raise ValueError("LLM did not return a GeneratedScene class")
                
                return code
            except Exception as exc:
                logger.error(f"Gemini generation failed: {exc}")
                # Re-raise the exception to allow auto mode to handle it properly
                raise exc

        # fallback / unsupported provider – return simple circle demo
        logger.info("Falling back to stub Manim code")
        return (
            "from manim import *\n\n"
            "class GeneratedScene(Scene):\n"
            "    def construct(self):\n"
            "        circle = Circle(radius=1, color=BLUE, fill_opacity=0.5)\n"
            "        self.play(Create(circle), run_time=2)\n"
            "        self.wait(1)\n"
        )

    async def _auto_mode_generate(self, original_prompt: str) -> str:
        """Auto mode with sophisticated fallback and self-correction system.
        
        Pipeline:
        1. Try Gemma (3 attempts with error correction)
        2. If fails: Rewrite prompt with Gemma, try again (3 attempts)
        3. If fails: Simplify prompt with Gemma, try again (3 attempts) 
        4. If fails: Try Gemini Flash Lite (1 attempt with error correction)
        5. If fails: Try Gemini Flash (1 attempt)
        6. If fails: Simplify prompt with Gemini Flash Lite, try Gemini Flash once more
        """
        logger.info("Starting auto mode generation pipeline...")
        
        # Phase 1: Gemma with error correction (3 attempts)
        logger.info("Phase 1: Trying Gemma with error correction...")
        result = await self._try_with_error_correction("gemma-3-27b-it", original_prompt, max_attempts=3)
        if result:
            logger.info("Phase 1 succeeded with Gemma")
            return result
        
        # Phase 2: Rewrite prompt with Gemma, then try again (3 attempts)
        logger.info("Phase 2: Rewriting prompt and trying again...")
        rewritten_prompt = await self._rewrite_prompt(original_prompt)
        if rewritten_prompt:
            result = await self._try_with_error_correction("gemma-3-27b-it", rewritten_prompt, max_attempts=3)
            if result:
                logger.info("Phase 2 succeeded with rewritten prompt")
                return result
        
        # Phase 3: Simplify prompt with Gemma, then try again (3 attempts)
        logger.info("Phase 3: Simplifying prompt and trying again...")
        simplified_prompt = await self._simplify_prompt(original_prompt)
        if simplified_prompt:
            result = await self._try_with_error_correction("gemma-3-27b-it", simplified_prompt, max_attempts=3)
            if result:
                logger.info("Phase 3 succeeded with simplified prompt")
                return result
        
        # Phase 4: Try Gemini Flash Lite (1 attempt with error correction)
        logger.info("Phase 4: Trying Gemini Flash Lite...")
        result = await self._try_with_error_correction("gemini-2.5-flash-lite", original_prompt, max_attempts=2)
        if result:
            logger.info("Phase 4 succeeded with Gemini Flash Lite")
            return result
        
        # Phase 5: Try Gemini Flash (1 attempt)
        logger.info("Phase 5: Trying Gemini Flash...")
        result = await self._try_single_generation("gemini-2.5-flash", original_prompt)
        if result:
            logger.info("Phase 5 succeeded with Gemini Flash")
            return result
        
        # Phase 6: Final attempt - Simplify with Flash Lite, then try Flash
        logger.info("Phase 6: Final attempt with simplified prompt...")
        final_simplified = await self._simplify_prompt_with_model(original_prompt, "gemini-2.5-flash-lite")
        if final_simplified:
            result = await self._try_single_generation("gemini-2.5-flash", final_simplified)
            if result:
                logger.info("Phase 6 succeeded with final simplified prompt")
                return result
        
        # If all phases fail, return a basic working example
        logger.error("All auto mode phases failed, returning fallback")
        return (
            "from manim import *\n\n"
            "class GeneratedScene(Scene):\n"
            "    def construct(self):\n"
            "        # Auto mode fallback - basic animation\n"
            "        text = Text('Auto Mode Fallback', font_size=48)\n"
            "        circle = Circle(radius=1, color=BLUE, fill_opacity=0.3)\n"
            "        \n"
            "        self.play(Write(text))\n"
            "        self.wait(1)\n"
            "        self.play(Create(circle))\n"
            "        self.wait(2)\n"
        )

    async def _try_with_error_correction(self, model: str, prompt: str, max_attempts: int = 3, video_errors: list = None) -> Optional[str]:
        """Try generating code with error correction loop and compilation validation."""
        current_prompt = prompt
        video_errors = video_errors or []
        
        # If we have video errors from previous attempts, incorporate them
        if video_errors:
            error_summary = "; ".join(video_errors[-3:])  # Use last 3 errors
            current_prompt = self._create_video_error_correction_prompt(prompt, error_summary)
            logger.info(f"Using video error correction prompt with {len(video_errors)} previous errors")
        
        for attempt in range(max_attempts):
            logger.info(f"Attempt {attempt + 1}/{max_attempts} with {model}")
            
            try:
                code = await self._try_single_generation(model, current_prompt)
                
                # If no code was generated, try next attempt
                if not code:
                    logger.warning(f"No code generated on attempt {attempt + 1}")
                    if attempt < max_attempts - 1:
                        current_prompt = self._create_error_correction_prompt(prompt, "", "No code was generated")
                    continue
                
                # Validate basic syntax first
                if not self._validate_basic_syntax(code):
                    logger.warning(f"Basic syntax validation failed on attempt {attempt + 1}")
                    if attempt < max_attempts - 1:
                        error_msg = self._analyze_code_issues(code)
                        current_prompt = self._create_error_correction_prompt(prompt, code, error_msg)
                        logger.info(f"Generated error correction prompt for attempt {attempt + 2}")
                    continue
                
                # Try to compile and validate the code more thoroughly
                compilation_result = await self._validate_code_compilation(code)
                if compilation_result["success"]:
                    logger.info(f"Code compilation successful on attempt {attempt + 1}")
                    return code
                else:
                    logger.warning(f"Code compilation failed on attempt {attempt + 1}: {compilation_result['error']}")
                    if attempt < max_attempts - 1:
                        current_prompt = self._create_error_correction_prompt(prompt, code, compilation_result['error'])
                        logger.info(f"Generated compilation error correction prompt for attempt {attempt + 2}")
                
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                if attempt < max_attempts - 1:
                    current_prompt = self._create_error_correction_prompt(prompt, "", str(e))
        
        return None

    async def _validate_code_compilation(self, code: str) -> dict:
        """Validate that the generated code can be compiled and has proper structure."""
        report = ValidationReportBuilder()

        try:
            # Try to compile the code
            compile(code, '<string>', 'exec')
            
            # Check for required elements
            if "class GeneratedScene" not in code:
                report.add_error("missing_generated_scene", "Missing GeneratedScene class")
            if "def construct(self)" not in code:
                report.add_error("missing_construct_method", "Missing construct method")
            if "from manim import" not in code:
                report.add_error("missing_manim_import", "Missing manim import")
            
            # Check for common issues that would cause runtime errors
            # Check for deprecated methods
            deprecated_methods = [
                "axes.add_labels()", "axes.add_coordinate_labels()", 
                "axes.plot_line()", "ShowCreation", "TexMobject"
            ]
            
            for method in deprecated_methods:
                if method in code:
                    report.add_error(
                        "deprecated_method",
                        f"Uses deprecated method: {method}",
                        evidence=method,
                    )
            
            # Check for common syntax issues
            if "self.play(" in code and "run_time" not in code:
                # This is just a warning, not a failure
                logger.info("Code uses self.play without explicit run_time")
            
            # Check for proper scene structure
            if "Scene" not in code and "ThreeDScene" not in code:
                report.add_error("invalid_scene_structure", "Scene class not properly defined")

            # Ensure there is at least one animation or addition command
            if "self.play(" not in code and "self.add(" not in code:
                report.add_error(
                    "missing_animation_actions",
                    "No animation or object addition commands found",
                )

            # Static (non-runtime) layout-risk checks.
            for risk in self._analyze_static_layout_risks(code):
                report.add_layout_risk(risk["code"], risk["message"], risk.get("evidence"))

            return report.to_result()
            
        except SyntaxError as e:
            report.add_error("syntax_error", f"Syntax error: {e}")
            return report.to_result()
        except Exception as e:
            report.add_error("compilation_error", f"Compilation error: {e}")
            return report.to_result()

    def _analyze_static_layout_risks(self, code: str) -> List[Dict[str, str]]:
        """Heuristic static checks for likely layout overlap/crowding/off-screen issues."""
        risks: List[Dict[str, str]] = []

        anchor_pattern = re.compile(r"\.(to_edge|to_corner)\(\s*(UP|DOWN|LEFT|RIGHT|UL|UR|DL|DR)\s*\)")
        anchor_counts: Dict[str, int] = {}
        for match in anchor_pattern.finditer(code):
            anchor = match.group(2)
            anchor_counts[anchor] = anchor_counts.get(anchor, 0) + 1
        for anchor, count in anchor_counts.items():
            if count >= 2:
                risks.append(
                    {
                        "code": "anchor_overlap_risk",
                        "message": f"Multiple objects target the same anchor ({anchor}); overlap is likely.",
                        "evidence": f"{anchor} used {count} times",
                    }
                )

        coord_pattern = re.compile(
            r"\.(move_to|shift)\(\s*\[\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)"
        )
        for match in coord_pattern.finditer(code):
            x_val = float(match.group(2))
            y_val = float(match.group(3))
            if abs(x_val) > 7.1 or abs(y_val) > 4.0:
                risks.append(
                    {
                        "code": "offscreen_coordinate_risk",
                        "message": "Coordinate appears outside the default frame; object may be off-screen.",
                        "evidence": match.group(0),
                    }
                )

        font_size_pattern = re.compile(r"font_size\s*=\s*(\d+(?:\.\d+)?)")
        large_fonts = [float(match.group(1)) for match in font_size_pattern.finditer(code) if float(match.group(1)) >= 72]
        if large_fonts:
            risks.append(
                {
                    "code": "large_text_crowding_risk",
                    "message": "Large text font sizes can cause crowding or clipping in a single scene.",
                    "evidence": f"font_size values: {', '.join(str(int(v)) for v in large_fonts)}",
                }
            )

        text_obj_count = len(re.findall(r"\b(Text|MathTex|Tex|Paragraph|MarkupText)\s*\(", code))
        fadeout_count = len(re.findall(r"\bFadeOut\s*\(", code))
        if text_obj_count >= 6 and fadeout_count < max(1, text_obj_count // 3):
            risks.append(
                {
                    "code": "text_density_crowding_risk",
                    "message": "High text object count with limited cleanup suggests crowding risk.",
                    "evidence": f"text_objects={text_obj_count}, fadeouts={fadeout_count}",
                }
            )

        return risks

    async def _try_single_generation(self, model: str, prompt: str) -> Optional[str]:
        """Try a single generation attempt."""
        try:
            return await self.generate_manim_code(prompt, model)
        except Exception as e:
            # Check if it's a 503 error (service overloaded)
            if "503" in str(e) or "UNAVAILABLE" in str(e) or "overloaded" in str(e).lower():
                logger.warning(f"Service overloaded (503) for {model}: {e}")
                return None  # Return None to allow auto mode to try other models
            else:
                logger.warning(f"Single generation failed with {model}: {e}")
                return None

    async def _rewrite_prompt(self, original_prompt: str) -> Optional[str]:
        """Rewrite the prompt using Gemma to make it clearer."""
        rewrite_prompt = (
            "Rewrite the following video description to be clearer and more specific for Manim code generation. "
            "Focus on concrete visual elements, animations, and mathematical concepts. "
            "Make it more detailed and technical while keeping the core intent. "
            "Return ONLY the rewritten description, no other text.\n\n"
            f"Original: {original_prompt}"
        )
        
        try:
            return await self._try_single_generation("gemma-3-27b-it", rewrite_prompt)
        except Exception as e:
            logger.warning(f"Prompt rewriting failed: {e}")
            return None

    async def _simplify_prompt(self, original_prompt: str) -> Optional[str]:
        """Simplify the prompt using Gemma."""
        return await self._simplify_prompt_with_model(original_prompt, "gemma-3-27b-it")

    async def _simplify_prompt_with_model(self, original_prompt: str, model: str) -> Optional[str]:
        """Simplify the prompt using specified model."""
        simplify_prompt = (
            "Simplify the following video description to focus on the most essential visual elements. "
            "Remove complex requirements and focus on basic animations that are easy to implement in Manim. "
            "Keep only the core concept and make it beginner-friendly. "
            "Return ONLY the simplified description, no other text.\n\n"
            f"Original: {original_prompt}"
        )
        
        try:
            return await self._try_single_generation(model, simplify_prompt)
        except Exception as e:
            logger.warning(f"Prompt simplification failed with {model}: {e}")
            return None

    def _validate_basic_syntax(self, code: str) -> bool:
        """Basic validation of generated code."""
        try:
            # Try to compile the code
            compile(code, '<string>', 'exec')
            
            # Check for required elements
            if "class GeneratedScene" not in code:
                return False
            if "def construct(self)" not in code:
                return False
            if "from manim import" not in code:
                return False
                
            return True
        except SyntaxError:
            return False
        except Exception:
            return False

    def _analyze_code_issues(self, code: str) -> str:
        """Analyze code to identify potential issues."""
        issues = []
        
        # Check for common deprecated methods
        deprecated_methods = [
            "axes.add_labels()", "axes.add_coordinate_labels()", 
            "axes.plot_line()", "ShowCreation", "TexMobject"
        ]
        
        for method in deprecated_methods:
            if method in code:
                issues.append(f"Uses deprecated method: {method}")
        
        # Check for syntax issues
        try:
            compile(code, '<string>', 'exec')
        except SyntaxError as e:
            issues.append(f"Syntax error: {e}")
        except Exception as e:
            issues.append(f"Code error: {e}")
        
        return "; ".join(issues) if issues else "Unknown issues detected"

    def _create_error_correction_prompt(self, original_prompt: str, failed_code: str, error_msg: str) -> str:
        """Create a prompt for error correction."""
        return (
            f"The previous code generation failed. Please fix the issues and generate working Manim code.\n\n"
            f"Original request: {original_prompt}\n\n"
            f"Previous code:\n{failed_code}\n\n"
            f"Error/Issues: {error_msg}\n\n"
            f"Please generate corrected Manim code that avoids these issues. "
            f"Use only modern Manim v0.19.0+ API methods. "
            f"Return ONLY the corrected Python code."
        )

    def _create_video_error_correction_prompt(self, original_prompt: str, video_errors: str) -> str:
        """Create a prompt for video compilation error correction."""
        return (
            f"The previous video generation attempts failed during compilation. Please generate simpler, more reliable Manim code.\n\n"
            f"Original request: {original_prompt}\n\n"
            f"Video compilation errors encountered: {video_errors}\n\n"
            f"CRITICAL FIXES NEEDED:\n"
            f"- Use ONLY 3D coordinates for all points: [x, y, 0] instead of [x, y]\n"
            f"- For Line objects, use: Line(start=[-3, 0, 0], end=[3, 0, 0])\n"
            f"- For positioning, use: object.move_to([x, y, 0])\n"
            f"- Avoid complex coordinate systems\n"
            f"- Use simple shapes and animations only\n"
            f"- Test all coordinates are 3D (x, y, z)\n\n"
            f"Please generate SIMPLER, more reliable Manim code that will definitely compile. "
            f"Focus on basic animations with proper 3D coordinates. "
            f"Return ONLY the corrected Python code."
        )

    async def generate_manim_code_with_video_validation(self, prompt: str, model: Optional[str] = None, video_errors: list = None, auto_config = None) -> str:
        """Generate Manim code with video generation error feedback.
        
        This method is used by the auto mode to incorporate video generation
        errors into the prompt engineering process.
        """
        model = model or "gemini-2.5-flash"
        
        if model == "auto":
            return await self._auto_mode_generate_with_video_errors(prompt, video_errors, auto_config)
        else:
            # For non-auto models, incorporate video errors if available
            if video_errors:
                enhanced_prompt = self._create_video_error_correction_prompt(prompt, "; ".join(video_errors[-3:]))
                return await self.generate_manim_code(enhanced_prompt, model)
            else:
                return await self.generate_manim_code(prompt, model)

    async def _auto_mode_generate_with_video_errors(self, original_prompt: str, video_errors: list = None, auto_config = None) -> str:
        """Auto mode with video error feedback integration."""
        # If auto_config is provided, use the new configurable method
        if auto_config is not None:
            return await self._auto_mode_generate_with_config(original_prompt, video_errors, auto_config)
        
        # Original implementation for backward compatibility
        logger.info("Starting auto mode generation pipeline with video error feedback...")
        video_errors = video_errors or []
        
        # Phase 1: Gemma with error correction (3 attempts) - incorporate video errors
        logger.info("Phase 1: Trying Gemma with error correction...")
        result = await self._try_with_error_correction("gemma-3-27b-it", original_prompt, max_attempts=3, video_errors=video_errors)
        if result:
            logger.info("Phase 1 succeeded with Gemma")
            return result
        
        # Phase 2: Rewrite prompt with Gemma, then try again (3 attempts)
        logger.info("Phase 2: Rewriting prompt and trying again...")
        rewritten_prompt = await self._rewrite_prompt(original_prompt)
        if rewritten_prompt:
            result = await self._try_with_error_correction("gemma-3-27b-it", rewritten_prompt, max_attempts=3, video_errors=video_errors)
            if result:
                logger.info("Phase 2 succeeded with rewritten prompt")
                return result
        
        # Phase 3: Simplify prompt with Gemma, then try again (3 attempts)
        logger.info("Phase 3: Simplifying prompt and trying again...")
        simplified_prompt = await self._simplify_prompt(original_prompt)
        if simplified_prompt:
            result = await self._try_with_error_correction("gemma-3-27b-it", simplified_prompt, max_attempts=3, video_errors=video_errors)
            if result:
                logger.info("Phase 3 succeeded with simplified prompt")
                return result
        
        # Phase 4: Try Gemini Flash Lite (2 attempts with error correction)
        logger.info("Phase 4: Trying Gemini Flash Lite...")
        result = await self._try_with_error_correction("gemini-2.5-flash-lite", original_prompt, max_attempts=2, video_errors=video_errors)
        if result:
            logger.info("Phase 4 succeeded with Gemini Flash Lite")
            return result
        
        # Phase 5: Try Gemini Flash (1 attempt)
        logger.info("Phase 5: Trying Gemini Flash...")
        if video_errors:
            enhanced_prompt = self._create_video_error_correction_prompt(original_prompt, "; ".join(video_errors[-3:]))
            result = await self._try_single_generation("gemini-2.5-flash", enhanced_prompt)
        else:
            result = await self._try_single_generation("gemini-2.5-flash", original_prompt)
        if result:
            logger.info("Phase 5 succeeded with Gemini Flash")
            return result
        
        # Phase 6: Final attempt - Simplify with Flash Lite, then try Flash
        logger.info("Phase 6: Final attempt with simplified prompt...")
        final_simplified = await self._simplify_prompt_with_model(original_prompt, "gemini-2.5-flash-lite")
        if final_simplified:
            if video_errors:
                enhanced_prompt = self._create_video_error_correction_prompt(final_simplified, "; ".join(video_errors[-3:]))
                result = await self._try_single_generation("gemini-2.5-flash", enhanced_prompt)
            else:
                result = await self._try_single_generation("gemini-2.5-flash", final_simplified)
            if result:
                logger.info("Phase 6 succeeded with final simplified prompt")
                return result
        
        # If all phases fail, return a basic working example
        logger.error("All auto mode phases failed, returning fallback")
        return (
            "from manim import *\n\n"
            "class GeneratedScene(Scene):\n"
            "    def construct(self):\n"
            "        # Auto mode fallback - basic animation with proper 3D coordinates\n"
            "        text = Text('Auto Mode Fallback', font_size=48)\n"
            "        circle = Circle(radius=1, color=BLUE, fill_opacity=0.3)\n"
            "        \n"
            "        self.play(Write(text))\n"
            "        self.wait(1)\n"
            "        self.play(Create(circle))\n"
            "        self.wait(2)\n"
        )

    async def _auto_mode_generate_with_config(self, original_prompt: str, video_errors: list = None, auto_config = None) -> str:
        """Configurable auto mode with video error feedback integration."""
        logger.info("Starting configurable auto mode generation pipeline...")
        video_errors = video_errors or []
        
        # Apply custom prompt modifiers if provided
        current_prompt = original_prompt
        if hasattr(auto_config, 'custom_prompt_modifiers'):
            for modifier in auto_config.custom_prompt_modifiers:
                current_prompt = f"{current_prompt}\n{modifier}"
        
        # Phase 1: Primary model with error correction
        primary_model = auto_config.preferred_models[0] if hasattr(auto_config, 'preferred_models') and auto_config.preferred_models else "gemma-3-27b-it"
        max_attempts = getattr(auto_config, 'max_llm_attempts_per_phase', 3)
        enable_video_feedback = getattr(auto_config, 'enable_video_error_feedback', True)
        
        logger.info(f"Phase 1: Trying {primary_model} with error correction...")
        result = await self._try_with_error_correction(
            primary_model, 
            current_prompt, 
            max_attempts=max_attempts, 
            video_errors=video_errors if enable_video_feedback else None
        )
        if result:
            logger.info(f"Phase 1 succeeded with {primary_model}")
            return result
        
        # Phase 2: Rewrite prompt (if enabled)
        if getattr(auto_config, 'enable_prompt_rewriting', True):
            logger.info("Phase 2: Rewriting prompt and trying again...")
            rewritten_prompt = await self._rewrite_prompt(current_prompt)
            if rewritten_prompt:
                result = await self._try_with_error_correction(
                    primary_model, 
                    rewritten_prompt, 
                    max_attempts=max_attempts, 
                    video_errors=video_errors if enable_video_feedback else None
                )
                if result:
                    logger.info("Phase 2 succeeded with rewritten prompt")
                    return result
        
        # Phase 3: Simplify prompt (if enabled)
        if getattr(auto_config, 'enable_prompt_simplification', True):
            logger.info("Phase 3: Simplifying prompt and trying again...")
            simplified_prompt = await self._simplify_prompt(current_prompt)
            if simplified_prompt:
                result = await self._try_with_error_correction(
                    primary_model, 
                    simplified_prompt, 
                    max_attempts=max_attempts, 
                    video_errors=video_errors if enable_video_feedback else None
                )
                if result:
                    logger.info("Phase 3 succeeded with simplified prompt")
                    return result
        
        # Phase 4: Try secondary models (if enabled and available)
        if getattr(auto_config, 'enable_gemini_fallback', True) and hasattr(auto_config, 'preferred_models') and len(auto_config.preferred_models) > 1:
            for i, model in enumerate(auto_config.preferred_models[1:], 1):
                logger.info(f"Phase {3+i}: Trying {model}...")
                result = await self._try_with_error_correction(
                    model, 
                    current_prompt, 
                    max_attempts=max_attempts, 
                    video_errors=video_errors if enable_video_feedback else None
                )
                if result:
                    logger.info(f"Phase {3+i} succeeded with {model}")
                    return result
        
        # Final fallback attempt with simplified prompt
        if getattr(auto_config, 'enable_prompt_simplification', True) and getattr(auto_config, 'enable_gemini_fallback', True):
            logger.info("Final phase: Simplified prompt with fallback model...")
            fallback_model = auto_config.preferred_models[-1] if hasattr(auto_config, 'preferred_models') and auto_config.preferred_models else "gemini-2.5-flash"
            final_simplified = await self._simplify_prompt_with_model(current_prompt, fallback_model)
            if final_simplified:
                if enable_video_feedback and video_errors:
                    enhanced_prompt = self._create_video_error_correction_prompt(final_simplified, "; ".join(video_errors[-3:]))
                    result = await self._try_single_generation(fallback_model, enhanced_prompt)
                else:
                    result = await self._try_single_generation(fallback_model, final_simplified)
                if result:
                    logger.info("Final phase succeeded with simplified prompt")
                    return result
        
        # If all phases fail, return a basic working example
        logger.error("All configurable auto mode phases failed, returning fallback")
        return (
            "from manim import *\n\n"
            "class GeneratedScene(Scene):\n"
            "    def construct(self):\n"
            "        # Auto mode fallback - basic animation with proper 3D coordinates\n"
        "        text = Text('Auto Mode Fallback', font_size=48)\n"
        "        circle = Circle(radius=1, color=BLUE, fill_opacity=0.3)\n"
        "        \n"
        "        self.play(Write(text))\n"
        "        self.wait(1)\n"
        "        self.play(Create(circle))\n"
        "        self.wait(2)\n"
        )


# Global LLM service instance
llm_service = LLMService()
