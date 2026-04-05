"""Helpers for building retry feedback and rewrite policy for auto mode."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Sequence

PREVIEW_QA_ERROR_PREFIX = "preview_qa_failed"
PREVIEW_QA_CODES_PREFIX = "preview_qa_codes="
_CODE_CORRECTNESS_MARKERS = (
    "compilation error:",
    "converted code error:",
    "syntax error",
    "missing_generated_scene",
    "missing_construct_method",
    "missing_manim_import",
    "invalid_scene_structure",
    "missing_animation_actions",
    "malformed_repeated_kwarg_assignment",
    "duplicate_keyword_assignment",
    "llm did not return valid generatedscene class",
)

_ISSUE_CODE_GUIDANCE: Dict[str, str] = {
    "border_crowding": (
        "Increase edge margins: keep all text/objects inside an 85% safe area and avoid to_edge/to_corner unless essential."
    ),
    "top_bottom_empty_imbalance": (
        "Redistribute vertical layout: avoid putting everything in the center; use top and bottom bands intentionally."
    ),
    "dense_horizontal_label_band": (
        "Reduce x-axis label density: use sparse ticks/labels and remove nonessential lower-band text near axes."
    ),
}


@dataclass(frozen=True)
class RetryPolicy:
    """Structured retry guidance payload derived from previous failures."""

    preview_failure_count: int
    code_failure_count: int
    preview_issue_codes: List[str]
    strictness_level: int
    simplification_rules: List[str]
    issue_specific_rules: List[str]


def extract_preview_issue_codes(video_errors: Sequence[str]) -> List[str]:
    """Extract unique preview QA issue codes from encoded retry errors."""
    seen = set()
    ordered: List[str] = []
    for error in video_errors:
        marker_index = error.find(PREVIEW_QA_CODES_PREFIX)
        if marker_index < 0:
            continue
        encoded = error[marker_index + len(PREVIEW_QA_CODES_PREFIX) :]
        encoded = encoded.split(";", 1)[0].strip()
        if not encoded:
            continue
        for raw_code in encoded.split(","):
            code = raw_code.strip()
            if code and code not in seen:
                seen.add(code)
                ordered.append(code)
    return ordered


def count_preview_failures(video_errors: Sequence[str]) -> int:
    """Count retries that failed due to preview QA."""
    return sum(1 for error in video_errors if PREVIEW_QA_ERROR_PREFIX in error)


def count_code_correctness_failures(video_errors: Sequence[str]) -> int:
    """Count retries that failed due to syntax/code-correctness problems."""
    total = 0
    for error in video_errors:
        normalized = error.lower()
        if PREVIEW_QA_ERROR_PREFIX in normalized:
            continue
        if any(marker in normalized for marker in _CODE_CORRECTNESS_MARKERS):
            total += 1
    return total


def build_retry_policy(video_errors: Sequence[str], *, formula_only: bool = False) -> RetryPolicy:
    """Build deterministic retry policy from retry history."""
    preview_failure_count = count_preview_failures(video_errors)
    code_failure_count = count_code_correctness_failures(video_errors)
    issue_codes = extract_preview_issue_codes(video_errors)

    if preview_failure_count >= 3:
        strictness_level = 3
        simplification_rules = [
            "Use a single focal object group at a time; no multi-block stacked layout.",
            "Use at most one short formula OR one short explanation sentence, not both.",
            "Avoid legends and dense axis labels entirely.",
        ]
    elif preview_failure_count >= 2:
        strictness_level = 2
        simplification_rules = [
            "Aggressively simplify layout to 2 visual regions max.",
            "Limit to one graph and one annotation line; remove extra labels.",
            "Prefer larger spacing and fewer simultaneous on-screen objects.",
        ]
    elif preview_failure_count >= 1:
        strictness_level = 1
        simplification_rules = [
            "Simplify object count and reduce text density.",
            "Prefer short labels and fewer decorative elements.",
        ]
    else:
        strictness_level = 0
        simplification_rules = [
            "Keep layout readable and avoid unnecessary visual complexity.",
        ]

    if formula_only and code_failure_count >= 1:
        strictness_level = max(strictness_level, min(3, code_failure_count))
        formula_rules = [
            "Formula-only code-correction mode: prioritize correctness over visual richness.",
            "Use a linear derivation flow with one MathTex line per step (max 4 steps).",
            "Avoid decorative mobjects, custom helper abstractions, and nested VGroup choreography.",
            "Fallback to safer staged reveals: Write/FadeIn per step, then FadeOut + Write for next step if needed.",
            "Use ReplacementTransform only for obvious 1:1 swaps; avoid TransformMatchingTex chains and key_map-heavy mappings.",
        ]
        simplification_rules = formula_rules + simplification_rules

    issue_specific_rules = [
        _ISSUE_CODE_GUIDANCE[code]
        for code in issue_codes
        if code in _ISSUE_CODE_GUIDANCE
    ]

    return RetryPolicy(
        preview_failure_count=preview_failure_count,
        code_failure_count=code_failure_count,
        preview_issue_codes=issue_codes,
        strictness_level=strictness_level,
        simplification_rules=simplification_rules,
        issue_specific_rules=issue_specific_rules,
    )


def format_retry_policy_lines(policy: RetryPolicy) -> List[str]:
    """Render policy as plain-text bullet lines for prompts."""
    lines = [
        (
            f"Retry strictness level: {policy.strictness_level} "
            f"(preview QA failures: {policy.preview_failure_count}; "
            f"code-correctness failures: {policy.code_failure_count})."
        ),
        "Layout simplification requirements:",
    ]
    lines.extend(f"- {rule}" for rule in policy.simplification_rules)

    if policy.preview_issue_codes:
        lines.append("Preview QA issue codes observed: " + ", ".join(policy.preview_issue_codes))
    if policy.issue_specific_rules:
        lines.append("Issue-specific fixes:")
        lines.extend(f"- {rule}" for rule in policy.issue_specific_rules)

    return lines


def encode_preview_qa_error(
    *,
    attempt: int,
    issue_codes: Iterable[str],
    issue_frames: Dict[str, int],
) -> str:
    """Build a compact, parseable retry error string for preview QA failures."""
    cleaned_codes = [code.strip() for code in issue_codes if code and code.strip()]
    if not cleaned_codes:
        cleaned_codes = ["preview_qa_failed"]

    frame_tokens = [
        f"{code}:{issue_frames.get(code, 0)}"
        for code in cleaned_codes
    ]

    return (
        f"{PREVIEW_QA_ERROR_PREFIX} attempt={attempt}; "
        f"{PREVIEW_QA_CODES_PREFIX}{','.join(cleaned_codes)}; "
        f"frames={','.join(frame_tokens)}"
    )
