from typing import Optional, Dict, Any, List, Tuple
from collections import Counter
import logging
import os
import re

from ..core.config import settings
from .retry_policy import build_retry_policy, format_retry_policy_lines, extract_preview_issue_codes
from .validation_report import ValidationReportBuilder

logger = logging.getLogger(__name__)


class LLMService:
    """Simple abstraction for calling different LLM providers.

    Currently works as a stub returning example Manim code. Extend this class
    to integrate with real providers such as Google Gemini, OpenAI, Anthropic, etc.
    """

    _GENERIC_SYSTEM_PROMPT = (
        "You are an expert Manim developer. Given a user description, "
        "return ONLY valid Python code that defines a Scene subclass named "
        "'GeneratedScene' which fulfils the request. "
        "Do not include markdown formatting, code blocks, or any explanations. "
        "Return only the raw Python code starting with 'from manim import *'."
    )

    _PORTRAIT_GRAPH_SCENE_GUARDRAILS = (
        "Portrait graph scene guardrails (educational 9:16 layout): "
        "Use sparse axis ticks and short labels; avoid dense tick labels. "
        "If using pi labels, include each value once only (no duplicate pi labels). "
        "Do not place legends in the top-right plot area; prefer below/left/outside the graph. "
        "Keep visible margins from all frame borders and avoid objects too close to edges. "
        "Avoid tall vertical stacks of title+axes+formula+paragraph; keep at most one short annotation below axes."
    )
    _FORMULA_ONLY_SCENE_GUARDRAILS = (
        "Formula-only derivation guardrails (readability first): "
        "Use a simple step-by-step derivation with short MathTex lines and clear spacing. "
        "Prefer 3 to 5 steps max, one focal equation block at a time. "
        "For portrait/Shorts-style requests, explicitly configure a 9:16 portrait scene using config.pixel_width = 1080, config.pixel_height = 1920, config.frame_width = 9, config.frame_height = 16. "
        "In portrait formula scenes, stack derivation steps vertically with VGroup(...).arrange(DOWN, aligned_edge=LEFT or CENTER) rather than laying terms out in long horizontal rows. "
        "Keep the equals signs and step starts visually aligned where practical. "
        "Avoid decorative backgrounds, extra shapes, rectangles, braces, underlines, dense text paragraphs, and visual overengineering unless explicitly requested. "
        "Prefer reliable animations: Write/FadeIn for reveals, ReplacementTransform for simple 1:1 swaps. "
        "Use TransformMatchingTex sparingly and only for clearly safe single-step token-preserving updates; "
        "avoid key_map-heavy transforms and long step-morph chains. "
        "If uncertain, use staged FadeOut + Write between steps. Keep object count low."
    )

    # Mapping of friendly model names to provider + model identifiers
    _MODEL_MAP: Dict[str, Dict[str, Any]] = {
        # provider, model name, additional kwargs if necessary
        "gemini-3.1-pro-preview": {"provider": "google", "model": "gemini-3.1-pro-preview"},
        "gemini-3-flash-preview": {"provider": "google", "model": "gemini-3-flash-preview"},
        "gemini-3.1-flash-lite-preview": {"provider": "google", "model": "gemini-3.1-flash-lite-preview"},
        "gemini-2.5-flash": {"provider": "google", "model": "gemini-2.5-flash"},
        "gemini-2.5-pro": {"provider": "google", "model": "gemini-2.5-pro"},
        "gemini-2.5-flash-lite": {"provider": "google", "model": "gemini-2.5-flash-lite"},
        "gemini-flash-latest": {"provider": "google", "model": "gemini-flash-latest"},
        "gemini-pro-latest": {"provider": "google", "model": "gemini-pro-latest"},
        "gemini-2.5-flash-latest": {"provider": "google", "model": "gemini-2.5-flash-latest"},
        "gemini-2.5-pro-latest": {"provider": "google", "model": "gemini-2.5-pro-latest"},
        "gemma-3-27b-it": {"provider": "google", "model": "gemma-3-27b-it"},
        "gemma-3-9b-it": {"provider": "google", "model": "gemma-3-9b-it"},
        "gpt-4o": {"provider": "openai", "model": "gpt-4o"},
        "auto": {"provider": "auto", "model": "auto"},
    }

    # Model-specific system prompts
    _SYSTEM_PROMPTS: Dict[str, str] = {
        # Gemini models - more up-to-date, need less guidance
        "gemini-3.1-pro-preview": _GENERIC_SYSTEM_PROMPT,
        "gemini-3-flash-preview": _GENERIC_SYSTEM_PROMPT,
        "gemini-3.1-flash-lite-preview": _GENERIC_SYSTEM_PROMPT,
        "gemini-2.5-flash": _GENERIC_SYSTEM_PROMPT,
        "gemini-2.5-pro": _GENERIC_SYSTEM_PROMPT,
        "gemini-2.5-flash-lite": _GENERIC_SYSTEM_PROMPT,
        "gemini-flash-latest": _GENERIC_SYSTEM_PROMPT,
        "gemini-pro-latest": _GENERIC_SYSTEM_PROMPT,
        "gemini-2.5-flash-latest": _GENERIC_SYSTEM_PROMPT,
        "gemini-2.5-pro-latest": _GENERIC_SYSTEM_PROMPT,
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
        "default": _GENERIC_SYSTEM_PROMPT,
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
                full_prompt = self._build_generation_prompt(system_prompt, prompt)
                
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

    def _build_generation_prompt(self, system_prompt: str, user_prompt: str) -> str:
        """Build model prompt and append portrait-graph guardrails when relevant."""
        prompt_sections = [system_prompt]
        if self._is_portrait_graph_scene_request(user_prompt):
            prompt_sections.append(self._PORTRAIT_GRAPH_SCENE_GUARDRAILS)
        if self._is_formula_only_scene_request(user_prompt):
            prompt_sections.append(self._FORMULA_ONLY_SCENE_GUARDRAILS)
            if self._is_portrait_request(user_prompt):
                prompt_sections.append(
                    "Portrait formula layout requirement: the final composition must read clearly in 9:16. "
                    "Do not spread derivation terms across the width of the frame. "
                    "Use vertically stacked equations centered in the portrait frame, with consistent alignment and generous side margins."
                )
        prompt_sections.append(f"User request: {user_prompt}")
        return "\n\n".join(prompt_sections)

    def _is_portrait_graph_scene_request(self, prompt: str) -> bool:
        """Detect portrait educational graph requests that benefit from extra layout guidance."""
        normalized = prompt.lower()
        has_graph_terms = any(
            term in normalized
            for term in (
                "graph",
                "plot",
                "axes",
                "axis",
                "coordinate",
                "function",
                "parabola",
                "sine",
                "cosine",
                "trigonometric",
            )
        )
        has_portrait_terms = any(
            term in normalized
            for term in (
                "portrait",
                "vertical",
                "9:16",
                "1080x1920",
                "1080 x 1920",
                "shorts",
                "reel",
                "tiktok",
            )
        )
        has_educational_terms = any(
            term in normalized
            for term in (
                "educational",
                "explain",
                "lesson",
                "teaching",
                "tutorial",
                "students",
                "class",
            )
        )
        return has_graph_terms and has_portrait_terms and has_educational_terms

    def _is_formula_only_scene_request(self, prompt: str) -> bool:
        """Detect formula-centric requests that should prefer lean derivation layouts."""
        normalized = prompt.lower()
        has_formula_terms = any(
            term in normalized
            for term in (
                "formula-only",
                "formula only",
                "derivation",
                "derive",
                "identity",
                "mathtex",
                "equation",
            )
        )
        has_graph_terms = any(
            term in normalized
            for term in (
                "graph",
                "plot",
                "axes",
                "axis",
                "coordinate plane",
                "numberplane",
            )
        )
        explicitly_excludes_graphs = any(
            term in normalized
            for term in (
                "no graph",
                "without graph",
                "no axes",
                "without axes",
            )
        )
        return has_formula_terms and (not has_graph_terms or explicitly_excludes_graphs)

    def _is_portrait_request(self, prompt: str) -> bool:
        """Detect portrait-oriented requests regardless of scene family."""
        normalized = prompt.lower()
        return any(
            term in normalized
            for term in (
                "portrait",
                "vertical",
                "9:16",
                "1080x1920",
                "1080 x 1920",
                "shorts",
                "reel",
                "tiktok",
            )
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
            current_prompt = self._create_video_error_correction_prompt(prompt, video_errors)
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
                    repaired_code, repaired_ok, repaired_error = await self._attempt_code_repair(
                        model=model,
                        original_prompt=prompt,
                        broken_code=code,
                        issue_text=self._analyze_code_issues(code),
                    )
                    if repaired_ok and repaired_code:
                        logger.info(f"Structured code repair succeeded on attempt {attempt + 1}")
                        return repaired_code
                    if attempt < max_attempts - 1:
                        error_msg = repaired_error or self._analyze_code_issues(code)
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
                    repaired_code, repaired_ok, repaired_error = await self._attempt_code_repair(
                        model=model,
                        original_prompt=prompt,
                        broken_code=code,
                        issue_text=compilation_result["error"],
                    )
                    if repaired_ok and repaired_code:
                        logger.info(f"Structured code repair succeeded after compilation failure on attempt {attempt + 1}")
                        return repaired_code
                    if attempt < max_attempts - 1:
                        current_prompt = self._create_error_correction_prompt(
                            prompt,
                            code,
                            repaired_error or compilation_result["error"],
                        )
                        logger.info(f"Generated compilation error correction prompt for attempt {attempt + 2}")

            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                if attempt < max_attempts - 1:
                    current_prompt = self._create_error_correction_prompt(prompt, "", str(e))

        return None

    async def _attempt_code_repair(
        self,
        *,
        model: str,
        original_prompt: str,
        broken_code: str,
        issue_text: str,
    ) -> Tuple[Optional[str], bool, str]:
        """Ask the model to repair previously generated code and revalidate it."""
        repair_prompt = self._create_structured_code_repair_prompt(
            original_prompt=original_prompt,
            broken_code=broken_code,
            issue_text=issue_text,
        )
        try:
            repaired_code = await self._try_single_generation(model, repair_prompt)
        except Exception as exc:
            return None, False, f"repair_generation_failed: {exc}"

        if not repaired_code:
            return None, False, "repair_generation_failed: no code returned"

        if not self._validate_basic_syntax(repaired_code):
            return None, False, self._analyze_code_issues(repaired_code)

        repaired_validation = await self._validate_code_compilation(repaired_code)
        if repaired_validation.get("success", False):
            return repaired_code, True, ""

        return None, False, repaired_validation.get("error", "repair_validation_failed")

    def _create_structured_code_repair_prompt(self, *, original_prompt: str, broken_code: str, issue_text: str) -> str:
        """Create a targeted repair prompt that asks the model to modify existing code."""
        extra_style_rules = ""
        if self._is_layout_or_style_error(issue_text):
            extra_style_rules = (
                "Additional layout/style repair requirements:\n"
                f"{self._summarize_layout_style_failures(original_prompt, [issue_text])}\n\n"
            )

        return (
            "You previously generated Manim code that needs repair.\n\n"
            "Task: modify the existing code to fix the issues below while preserving the original educational intent.\n"
            "Do NOT start from scratch unless the code is unusable.\n"
            "Think like a code repair model: inspect the code, fix the smallest necessary set of problems, and return the full corrected file.\n"
            "Return ONLY raw Python code beginning with 'from manim import *'.\n\n"
            f"Original user request:\n{original_prompt}\n\n"
            f"Detected issues:\n{issue_text}\n\n"
            "Repair requirements:\n"
            "- Keep class name GeneratedScene.\n"
            "- Preserve working parts when possible.\n"
            "- Remove or replace unsupported/deprecated Manim APIs.\n"
            "- If layout/readability is part of the issue, simplify the layout instead of adding more objects.\n"
            "- For formula scenes, prefer MathTex, portrait-safe spacing, vertical stacking, and no decorative highlight shapes unless explicitly requested.\n"
            "- If an element causes errors or clutter, delete it rather than improvising something flashy.\n\n"
            f"{extra_style_rules}"
            f"Code to repair:\n{broken_code}"
        )

    async def _validate_code_compilation(self, code: str) -> dict:
        """Validate that the generated code can be compiled and has proper structure."""
        report = ValidationReportBuilder()
        for issue in self._analyze_static_code_correctness_issues(code):
            report.add_error(issue["code"], issue["message"], issue.get("evidence"))

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

    def _analyze_static_code_correctness_issues(self, code: str) -> List[Dict[str, str]]:
        """Detect malformed repeated-kwarg constructs seen in generated code."""
        issues: List[Dict[str, str]] = []

        repeated_kwarg_token_pattern = re.compile(r"\b([A-Za-z_]\w*)\s*=\s*\1\s*=")
        repeated_token_matches = list(repeated_kwarg_token_pattern.finditer(code))
        if repeated_token_matches:
            evidence = ", ".join(match.group(0) for match in repeated_token_matches[:3])
            issues.append(
                {
                    "code": "malformed_repeated_kwarg_assignment",
                    "message": "Malformed repeated keyword assignment pattern detected (e.g., color= color=).",
                    "evidence": evidence,
                }
            )

        duplicate_kwarg_pattern = re.compile(
            r"\b([A-Za-z_]\w*)\s*=\s*[^,\n()]+,\s*\1\s*=",
            re.MULTILINE,
        )
        duplicate_kwarg_matches = list(duplicate_kwarg_pattern.finditer(code))
        if duplicate_kwarg_matches:
            evidence = ", ".join(match.group(0) for match in duplicate_kwarg_matches[:3])
            issues.append(
                {
                    "code": "duplicate_keyword_assignment",
                    "message": "Duplicate keyword argument assignment detected inside a call.",
                    "evidence": evidence,
                }
            )

        return issues

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

        # Graph-heavy vertical scene heuristics (static/pattern-based only).
        has_graph_context = bool(
            re.search(r"\b(Axes|NumberPlane|ComplexPlane)\s*\(", code)
            or re.search(r"\.(plot|get_graph)\s*\(", code)
        )
        has_title_object = bool(re.search(r"\b(title|heading)\w*\s*=\s*(Text|Tex|MathTex|Title)\s*\(", code, re.IGNORECASE))
        title_up_anchor_count = len(
            re.findall(
                r"\b(title|heading)\w*\.(to_edge|to_corner)\(\s*(UP|UL|UR)\s*\)",
                code,
                re.IGNORECASE,
            )
        )
        has_formula_or_explanation = bool(
            re.search(
                r"\b(formula|equation|eqn|explanation|description|desc|annotation|note)\w*\s*=\s*(Text|MathTex|Tex|Paragraph|MarkupText)\s*\(",
                code,
                re.IGNORECASE,
            )
        )

        down_next_to_count = len(re.findall(r"\.next_to\([^)]*,\s*DOWN\b", code))
        below_axes_count = len(re.findall(r"\.next_to\(\s*\w*(axes|axis)\w*\s*,\s*DOWN\b", code, re.IGNORECASE))
        below_axes_annotation_count = len(
            re.findall(
                r"\b(formula|equation|eqn|annotation|text|description|desc|explanation|note)\w*\.next_to\(\s*\w*(axes|axis)\w*\s*,\s*DOWN\b",
                code,
                re.IGNORECASE,
            )
        )
        below_axes_annotation_count += len(
            re.findall(
                r"\b(formula|equation|eqn|annotation|text|description|desc|explanation|note)\w*\s*=\s*(Text|MathTex|Tex|Paragraph|MarkupText)\s*\([^)]*\)\.next_to\(\s*\w*(axes|axis)\w*\s*,\s*DOWN\b",
                code,
                re.IGNORECASE,
            )
        )

        graph_label_count = len(re.findall(r"\.get_graph_label\s*\(", code))
        axis_label_count = len(re.findall(r"\.get_(x_axis_label|y_axis_label|axis_labels)\s*\(", code))

        has_legend_var = bool(re.search(r"\blegend\w*\s*=", code, re.IGNORECASE))
        legend_corner_like_count = len(
            re.findall(
                r"\blegend\w*\.(to_corner\(\s*(UR|UL)\s*\)|to_edge\(\s*(RIGHT|UP)\s*\)|next_to\([^)]*,\s*(UR|UP|RIGHT)\b)",
                code,
                re.IGNORECASE,
            )
        )

        if has_graph_context and (has_title_object or title_up_anchor_count > 0) and has_formula_or_explanation and down_next_to_count >= 2:
            risks.append(
                {
                    "code": "graph_vertical_stack_crowding_risk",
                    "message": "Graph scene stacks title + graph + formula/explanation vertically; crowding risk in portrait layouts.",
                    "evidence": (
                        f"title_up={title_up_anchor_count}, formula_or_explanation={has_formula_or_explanation}, "
                        f"next_to_down={down_next_to_count}"
                    ),
                }
            )

        if (
            has_graph_context
            and graph_label_count > 0
            and (has_title_object or title_up_anchor_count > 0)
            and (axis_label_count > 0 or has_formula_or_explanation or below_axes_count > 0)
        ):
            risks.append(
                {
                    "code": "graph_label_collision_risk",
                    "message": "get_graph_label is used in a busy graph scene (title/axes/formula); label collision risk is elevated.",
                    "evidence": (
                        f"graph_labels={graph_label_count}, axis_labels={axis_label_count}, "
                        f"title={has_title_object or title_up_anchor_count > 0}, below_axes={below_axes_count}"
                    ),
                }
            )

        if has_graph_context and has_legend_var and legend_corner_like_count > 0:
            risks.append(
                {
                    "code": "legend_plot_overlap_risk",
                    "message": "Legend positioned in/near upper-right plot area may overlap graph content.",
                    "evidence": f"legend_corner_like_placements={legend_corner_like_count}",
                }
            )

        if down_next_to_count >= 4:
            risks.append(
                {
                    "code": "vertical_chain_crowding_risk",
                    "message": "Many next_to(..., DOWN, ...) placements indicate a tall vertical chain likely to overflow.",
                    "evidence": f"next_to_down={down_next_to_count}",
                }
            )

        if has_graph_context and below_axes_annotation_count > 0 and (down_next_to_count >= 3 or (has_title_object and has_formula_or_explanation)):
            risks.append(
                {
                    "code": "below_axes_annotation_overflow_risk",
                    "message": "Formula/text annotations below axes in a tall graph scene can clip or fall off-screen.",
                    "evidence": (
                        f"below_axes_annotations={below_axes_annotation_count}, next_to_down={down_next_to_count}, "
                        f"title={has_title_object}"
                    ),
                }
            )

        # Formula-only animation safety heuristics (static/pattern-based only).
        mathtex_count = len(re.findall(r"\b(MathTex|Tex)\s*\(", code))
        text_count = len(re.findall(r"\bText\s*\(", code))
        formula_only_context = (
            not has_graph_context
            and mathtex_count >= 2
            and text_count <= 2
        )
        if formula_only_context:
            transform_matching_count = len(re.findall(r"\bTransformMatchingTex\s*\(", code))
            replacement_transform_count = len(re.findall(r"\bReplacementTransform\s*\(", code))
            transform_count = len(re.findall(r"\bTransform\s*\(", code))
            total_morph_count = transform_matching_count + replacement_transform_count + transform_count
            key_map_occurrence_count = len(re.findall(r"\bkey_map\s*=", code))

            if transform_matching_count >= 2:
                risks.append(
                    {
                        "code": "formula_transform_matching_chain_risk",
                        "message": (
                            "Formula-only scene uses multiple TransformMatchingTex steps; long morph chains are fragile. "
                            "Prefer staged Write/FadeIn or simple ReplacementTransform."
                        ),
                        "evidence": f"TransformMatchingTex calls={transform_matching_count}",
                    }
                )

            if key_map_occurrence_count > 0:
                key_map_entry_counts = [
                    len(re.findall(r":", snippet))
                    for snippet in re.findall(r"key_map\s*=\s*\{([^}]*)\}", code, re.DOTALL)
                ]
                max_key_map_entries = max(key_map_entry_counts, default=0)
                if key_map_occurrence_count >= 2 or max_key_map_entries >= 3:
                    risks.append(
                        {
                            "code": "formula_key_map_transform_risk",
                            "message": (
                                "Formula-only scene relies on key_map-heavy TransformMatchingTex mapping; "
                                "this is brittle across tokenization differences."
                            ),
                            "evidence": (
                                f"key_map_usages={key_map_occurrence_count}, "
                                f"max_key_map_entries={max_key_map_entries}"
                            ),
                        }
                    )

            if transform_matching_count >= 3 or (total_morph_count >= 5 and replacement_transform_count <= 1):
                risks.append(
                    {
                        "code": "formula_complex_step_morph_risk",
                        "message": (
                            "Formula-only derivation uses complex step morphing. "
                            "Prefer fewer morphs and safer staged reveals between steps."
                        ),
                        "evidence": (
                            f"TransformMatchingTex={transform_matching_count}, "
                            f"ReplacementTransform={replacement_transform_count}, Transform={transform_count}"
                        ),
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

        for issue in self._analyze_static_code_correctness_issues(code):
            issues.append(issue["message"])
        
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
        formula_only = self._is_formula_only_scene_request(original_prompt)
        is_code_correctness_failure = self._is_code_correctness_error(error_msg)
        extra_rules = ""
        if formula_only and is_code_correctness_failure:
            extra_rules = (
                "Formula-only retry mode (strict): simplify aggressively. "
                "Use 1 MathTex object per derivation step, max 4 steps total, "
                "no decorative objects, and no chained helper abstractions. "
                "Fallback pattern: staged reveals with Write/FadeIn; use ReplacementTransform only for obvious 1:1 swaps; "
                "avoid TransformMatchingTex chains and key_map mapping.\n\n"
            )

        return (
            f"The previous code generation failed. Please fix the issues and generate working Manim code.\n\n"
            f"Original request: {original_prompt}\n\n"
            f"Previous code:\n{failed_code}\n\n"
            f"Error/Issues: {error_msg}\n\n"
            f"{extra_rules}"
            f"Please generate corrected Manim code that avoids these issues. "
            f"Use only modern Manim v0.19.0+ API methods. "
            f"Return ONLY the corrected Python code."
        )

    def _create_video_error_correction_prompt(self, original_prompt: str, video_errors: Any) -> str:
        """Create a prompt for video compilation error correction."""
        if isinstance(video_errors, list):
            error_history = [str(item).strip() for item in video_errors if str(item).strip()]
        else:
            text = str(video_errors).strip()
            error_history = [text] if text else []

        policy = build_retry_policy(
            error_history,
            formula_only=self._is_formula_only_scene_request(original_prompt),
        )
        policy_lines = "\n".join(format_retry_policy_lines(policy))
        error_summary = "; ".join(error_history[-4:]) if error_history else "None"
        style_guidance = self._summarize_layout_style_failures(original_prompt, error_history)
        repair_memory = self._summarize_repair_memory(error_history)

        return (
            f"The previous generation attempt(s) failed. Generate corrected, more robust Manim code.\n\n"
            f"Original request: {original_prompt}\n\n"
            f"Recent failures: {error_summary}\n\n"
            f"RETRY POLICY (must follow strictly):\n"
            f"{policy_lines}\n\n"
            f"LAYOUT / STYLE REPAIR PRIORITIES:\n"
            f"{style_guidance}\n\n"
            f"REPAIR MEMORY:\n"
            f"{repair_memory or '- No repeated failure pattern detected yet.'}\n\n"
            f"CRITICAL COMPATIBILITY FIXES:\n"
            f"- Use ONLY 3D coordinates for all points: [x, y, 0] instead of [x, y]\n"
            f"- For Line objects, use: Line(start=[-3, 0, 0], end=[3, 0, 0])\n"
            f"- For positioning, use: object.move_to([x, y, 0])\n"
            f"- Avoid complex coordinate systems\n"
            f"- Use simple shapes and animations only\n"
            f"- Test all coordinates are 3D (x, y, z)\n\n"
            f"Generate simpler, readable Manim code that compiles and follows the retry policy. "
            f"Return ONLY the corrected Python code."
        )

    def _is_code_correctness_error(self, error_msg: str) -> bool:
        """Classify whether retry failure text indicates syntax/code-correctness issues."""
        normalized = error_msg.lower()
        code_markers = (
            "compilation error",
            "converted code error",
            "syntax error",
            "missing generatedscene",
            "missing construct",
            "missing manim import",
            "invalid scene structure",
            "missing animation",
            "keyword assignment",
            "generatedscene class",
        )
        return any(marker in normalized for marker in code_markers)

    def _is_layout_or_style_error(self, error_msg: str) -> bool:
        """Classify whether retry failure text indicates layout/style correctness issues."""
        normalized = error_msg.lower()
        style_markers = (
            "preview_qa_failed",
            "border_crowding",
            "top_bottom_empty_imbalance",
            "dense_horizontal_label_band",
            "layout",
            "alignment",
            "misaligned",
            "portrait",
            "orientation",
            "horizontal",
            "highlight",
            "rectangle",
            "box",
            "decorative",
            "clutter",
            "crowding",
        )
        return any(marker in normalized for marker in style_markers)

    def _summarize_layout_style_failures(self, original_prompt: str, video_errors: List[str]) -> str:
        """Build deterministic layout/style repair guidance from retry history."""
        issue_codes = extract_preview_issue_codes(video_errors)
        lines: List[str] = []

        if self._is_portrait_request(original_prompt):
            lines.append("Portrait requirement: keep explicit 9:16 portrait config and avoid wide horizontal composition.")
        if self._is_formula_only_scene_request(original_prompt):
            lines.append("Formula requirement: use MathTex, vertically stacked derivation steps, and cleaner equation alignment.")
            lines.append("Do not add decorative highlight rectangles, boxes, braces, or extra shapes unless explicitly requested.")

        if "dense_horizontal_label_band" in issue_codes:
            lines.append("Reduce dense lower-band/horizontal clutter; do not spread formula terms across the frame width.")
        if "border_crowding" in issue_codes:
            lines.append("Increase safe margins and keep all content away from frame edges.")
        if "top_bottom_empty_imbalance" in issue_codes:
            lines.append("Redistribute content vertically so the composition feels balanced in portrait framing.")

        for raw in video_errors[-6:]:
            lower = str(raw).lower()
            if "alignment" in lower or "misaligned" in lower:
                lines.append("Fix alignment: keep derivation steps in a consistent equation column with stable left/equals alignment.")
            if "highlight" in lower or "rectangle" in lower or "box" in lower:
                lines.append("Remove decorative highlight shapes and use simpler emphasis.")
            if "horizontal" in lower or "orientation" in lower:
                lines.append("Avoid horizontal layouts for portrait scenes; prefer vertical composition.")
            if "mathtex" in lower and "text" in lower:
                lines.append("Prefer MathTex for equations instead of Text.")

        strategy_lines = self._build_quality_rewrite_strategy_lines(video_errors)
        lines.extend(strategy_lines)

        if not lines:
            lines.append("Simplify layout and remove nonessential decorative elements.")

        deduped: List[str] = []
        seen = set()
        for line in lines:
            if line not in seen:
                seen.add(line)
                deduped.append(line)
        return "\n".join(f"- {line}" for line in deduped)

    def _build_quality_rewrite_strategy_lines(self, quality_errors: List[str]) -> List[str]:
        """Map quality risk codes to concrete rewrite strategies for targeted repair."""
        lines: List[str] = []
        for raw in quality_errors:
            item = str(raw).strip().lower()
            if not item:
                continue
            if "portrait_orientation_missing" in item:
                lines.append(
                    "Rewrite strategy: inject explicit portrait config (pixel_width=1080, pixel_height=1920, frame_width=9, frame_height=16) near the top of the file."
                )
            if "formula_uses_text_not_mathtex" in item:
                lines.append(
                    "Rewrite strategy: replace equation Text(...) objects with MathTex(...) while preserving the derivation content."
                )
            if "decorative_highlight_box" in item:
                lines.append(
                    "Rewrite strategy: delete decorative Rectangle/SurroundingRectangle highlight objects and use color/emphasis on the final equation instead."
                )
            if "horizontal_formula_layout" in item or "wide_horizontal_chain" in item:
                lines.append(
                    "Rewrite strategy: replace horizontal row layout with a vertical derivation block using VGroup(...).arrange(DOWN, aligned_edge=LEFT or CENTER)."
                )
            if "weak_equation_alignment" in item:
                lines.append(
                    "Rewrite strategy: enforce a stable equation column by explicitly aligning left edges or equals signs across derivation steps."
                )
            if "dense_horizontal_label_band" in item:
                lines.append(
                    "Rewrite strategy: reduce dense lower-band content and keep formula groups compact and centered."
                )
            if "border_crowding" in item:
                lines.append(
                    "Rewrite strategy: increase margins and pull objects inward from edges before adding any new content."
                )
            if "top_bottom_empty_imbalance" in item:
                lines.append(
                    "Rewrite strategy: redistribute objects vertically to use portrait space more evenly."
                )
        return lines

    def _summarize_repair_memory(self, error_history: List[str]) -> str:
        """Summarize repeated failures/strategies so retries can escalate instead of looping."""
        normalized = [str(item).strip().lower() for item in error_history if str(item).strip()]
        counter = Counter(normalized)
        lines: List[str] = []

        repeated_quality = [item for item, count in counter.items() if count >= 2 and any(token in item for token in (
            "portrait_orientation_missing",
            "formula_uses_text_not_mathtex",
            "decorative_highlight_box",
            "horizontal_formula_layout",
            "wide_horizontal_chain",
            "weak_equation_alignment",
            "preview_qa_failed",
        ))]
        if repeated_quality:
            lines.append("Repeated quality failures detected:")
            lines.extend(f"- {item}" for item in repeated_quality[:5])
            lines.append("Escalation rule: do not repeat the same layout approach that caused these failures.")
            lines.append("Escalation rule: prefer structural rewrites over cosmetic tweaks on the next attempt.")

        repeated_strategies = [item for item, count in counter.items() if count >= 2 and "rewrite strategy:" in item]
        if repeated_strategies:
            lines.append("Previously suggested rewrite strategies repeated without success:")
            lines.extend(f"- {item}" for item in repeated_strategies[:5])
            lines.append("Escalation rule: combine or strengthen the next repair instead of retrying the same single fix.")

        return "\n".join(lines)

    def analyze_quality_risks(self, *, prompt: str, code: str) -> List[str]:
        """Detect non-blocking but undesirable style/layout qualities that should trigger repair."""
        risks: List[str] = []
        normalized = code.lower()

        if self._is_portrait_request(prompt):
            portrait_config_present = all(
                token in code
                for token in (
                    "config.pixel_width = 1080",
                    "config.pixel_height = 1920",
                    "config.frame_width = 9",
                    "config.frame_height = 16",
                )
            )
            if not portrait_config_present:
                risks.append("portrait_orientation_missing: expected explicit 9:16 portrait config")

        if self._is_formula_only_scene_request(prompt):
            if "text(" in normalized and "mathtex(" not in normalized:
                risks.append("formula_uses_text_not_mathtex: equations should use MathTex")
            if re.search(r"\b(rectangle|surroundingrectangle)\s*\(", normalized):
                risks.append("decorative_highlight_box: remove decorative rectangles/boxes in formula scenes")
            if "arrange(right" in normalized:
                risks.append("horizontal_formula_layout: avoid right-arranged horizontal formula composition in portrait scenes")
            if ".next_to(" in normalized and "right" in normalized and self._is_portrait_request(prompt):
                right_placements = len(re.findall(r"\.next_to\([^)]*,\s*RIGHT\b", code))
                if right_placements >= 2:
                    risks.append("wide_horizontal_chain: too many RIGHT-based placements for a portrait derivation")
            if "aligned_edge=left" not in normalized and "aligned_edge=center" not in normalized and "arrange(down" in normalized:
                risks.append("weak_equation_alignment: vertical derivation stack lacks explicit alignment")

        return risks

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
                enhanced_prompt = self._create_video_error_correction_prompt(prompt, video_errors)
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
            enhanced_prompt = self._create_video_error_correction_prompt(original_prompt, video_errors)
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
                enhanced_prompt = self._create_video_error_correction_prompt(final_simplified, video_errors)
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
                    enhanced_prompt = self._create_video_error_correction_prompt(final_simplified, video_errors)
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
