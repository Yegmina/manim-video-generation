from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


class VerticalRepairClient:
    """Lightweight Gemini repair client for the deterministic vertical subsystem."""

    MODELS = [
        "gemini-3.1-pro-preview",
        "gemini-3-flash-preview",
        "gemini-2.5-flash",
    ]

    def repair_code(self, *, original_prompt: str, broken_code: str, issue_text: str) -> str:
        prompt = self._build_repair_prompt(
            original_prompt=original_prompt,
            broken_code=broken_code,
            issue_text=issue_text,
        )

        api_key = os.getenv("GOOGLE_API_KEY") or self._load_repo_google_api_key()
        
        if not api_key:
            raise RuntimeError("GOOGLE_API_KEY not found for vertical repair client")

        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        last_error: Optional[Exception] = None
        for model in self.MODELS:
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=[
                        types.Content(
                            role="user",
                            parts=[types.Part.from_text(text=prompt)],
                        )
                    ],
                )
                code = (response.text or "").strip()
                if code.startswith("```python"):
                    code = code[9:]
                if code.startswith("```"):
                    code = code[3:]
                if code.endswith("```"):
                    code = code[:-3]
                code = code.strip()
                if "class GeneratedScene" not in code:
                    raise RuntimeError(f"{model} did not return GeneratedScene code")
                return code
            except Exception as exc:  # pragma: no cover - network/provider dependent
                last_error = exc
                continue
        raise RuntimeError(f"All repair models failed: {last_error}")

    def _load_repo_google_api_key(self) -> Optional[str]:
        env_path = Path(__file__).resolve().parents[2] / ".env"
        if not env_path.exists():
            return None
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            if key.strip() == "GOOGLE_API_KEY":
                return value.strip().strip('"').strip("'")
        return None

    def _build_repair_prompt(self, *, original_prompt: str, broken_code: str, issue_text: str) -> str:
        extra_rules = ""
        lowered = issue_text.lower()
        if "dense_horizontal_label_band" in lowered:
            extra_rules += (
                "- Dense lower horizontal band detected: aggressively reduce lower-band content.\n"
                "- Do NOT place equation/info directly below the x-axis if that creates a dense stripe.\n"
                "- Prefer moving the equation/info into a compact upper-right or upper-left annotation card away from axis labels.\n"
                "- If necessary, keep only one short phase/state label and remove extra lower text.\n"
                "- Keep the graph readable, but simplify the annotation layout more aggressively than before.\n"
            )
        return (
            "You are fixing Manim code for a portrait educational short.\n\n"
            "Modify the existing code to fix the detected visual/layout issues while preserving the scene intent.\n"
            "Do not start over unless absolutely necessary.\n"
            "Return ONLY raw Python code beginning with 'from manim import *'.\n\n"
            f"Original task:\n{original_prompt}\n\n"
            f"Detected issues:\n{issue_text}\n\n"
            "Requirements:\n"
            "- Keep class name GeneratedScene.\n"
            "- Keep 9:16 portrait output.\n"
            "- Avoid border overflow and collisions.\n"
            "- If graph labels and equation overlap, separate them into distinct vertical regions.\n"
            "- Use MathTex for equations/formulas where appropriate.\n"
            "- Remove nonessential decorative or redundant elements.\n"
            f"{extra_rules}\n"
            f"Code to repair:\n{broken_code}"
        )
