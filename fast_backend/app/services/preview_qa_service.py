"""
Preview render QA service for generated Manim scenes.

This module provides a practical first-pass visual QA loop:
1. Render low-quality preview video.
2. Extract representative frames with ffmpeg.
3. Run lightweight frame heuristics without external vision models.
4. Return a structured report suitable for metadata logging/storage.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence

import numpy as np
from PIL import Image

from ..core.config import settings
from .manim_code_converter import convert_manim_code

logger = logging.getLogger(__name__)


@dataclass
class FrameHeuristicIssue:
    code: str
    score: float
    message: str

    def to_dict(self) -> Dict[str, object]:
        return {
            "code": self.code,
            "score": round(self.score, 4),
            "message": self.message,
        }


@dataclass
class FrameMetrics:
    width: int
    height: int
    foreground_ratio: float
    border_foreground_ratio: float
    top_band_foreground_ratio: float
    bottom_band_foreground_ratio: float
    middle_band_foreground_ratio: float
    edge_density: float
    horizontal_band_peak_ratio: float

    def to_dict(self) -> Dict[str, object]:
        return {
            "width": self.width,
            "height": self.height,
            "foreground_ratio": round(self.foreground_ratio, 6),
            "border_foreground_ratio": round(self.border_foreground_ratio, 6),
            "top_band_foreground_ratio": round(self.top_band_foreground_ratio, 6),
            "bottom_band_foreground_ratio": round(self.bottom_band_foreground_ratio, 6),
            "middle_band_foreground_ratio": round(self.middle_band_foreground_ratio, 6),
            "edge_density": round(self.edge_density, 6),
            "horizontal_band_peak_ratio": round(self.horizontal_band_peak_ratio, 6),
        }


def analyze_frame_heuristics(frame_rgb: np.ndarray) -> Dict[str, object]:
    """
    Analyze one RGB frame and return metrics + heuristic issues.

    This function is intentionally pure so it can be tested without rendering.
    """
    if frame_rgb.ndim != 3 or frame_rgb.shape[2] != 3:
        raise ValueError("Expected an RGB frame shaped [H, W, 3]")

    height, width, _ = frame_rgb.shape
    gray = (
        0.299 * frame_rgb[:, :, 0].astype(np.float32)
        + 0.587 * frame_rgb[:, :, 1].astype(np.float32)
        + 0.114 * frame_rgb[:, :, 2].astype(np.float32)
    )

    # Manim scenes are commonly dark background with bright text/objects.
    foreground_mask = gray >= 42.0
    foreground_ratio = float(foreground_mask.mean())

    margin_y = max(1, int(height * 0.06))
    margin_x = max(1, int(width * 0.05))
    border_mask = np.zeros((height, width), dtype=bool)
    border_mask[:margin_y, :] = True
    border_mask[-margin_y:, :] = True
    border_mask[:, :margin_x] = True
    border_mask[:, -margin_x:] = True
    border_foreground_ratio = float(np.logical_and(foreground_mask, border_mask).mean())

    band_h = max(1, int(height * 0.18))
    middle_start = height // 3
    middle_end = min(height, middle_start + height // 3)
    top_band_ratio = float(foreground_mask[:band_h, :].mean())
    bottom_band_ratio = float(foreground_mask[-band_h:, :].mean())
    middle_band_ratio = float(foreground_mask[middle_start:middle_end, :].mean())

    # Lightweight edge density for text-like/detail-like occupancy.
    dx = np.abs(np.diff(gray, axis=1))
    dy = np.abs(np.diff(gray, axis=0))
    edge_mask = np.zeros((height, width), dtype=bool)
    edge_mask[:, 1:] |= dx > 18.0
    edge_mask[1:, :] |= dy > 18.0
    edge_density = float(edge_mask.mean())

    row_edge_density = edge_mask.mean(axis=1)
    lower_start = int(height * 0.58)
    lower_end = int(height * 0.9)
    candidate_rows = row_edge_density[lower_start:lower_end]
    peak = float(candidate_rows.max()) if candidate_rows.size else 0.0
    baseline = float(np.mean(candidate_rows)) if candidate_rows.size else 0.0
    spread = float(np.std(candidate_rows)) if candidate_rows.size else 0.0
    peak_ratio = peak / (baseline + 1e-6)
    middle_rows = row_edge_density[int(height * 0.32) : int(height * 0.58)]
    middle_row_baseline = float(np.mean(middle_rows)) if middle_rows.size else 0.0
    lower_vs_middle_peak_ratio = peak / (middle_row_baseline + 1e-6)

    high_row_mask = candidate_rows > (baseline + 1.2 * spread)
    max_high_run = 0
    current_run = 0
    for is_high in high_row_mask:
        if is_high:
            current_run += 1
            max_high_run = max(max_high_run, current_run)
        else:
            current_run = 0

    metrics = FrameMetrics(
        width=width,
        height=height,
        foreground_ratio=foreground_ratio,
        border_foreground_ratio=border_foreground_ratio,
        top_band_foreground_ratio=top_band_ratio,
        bottom_band_foreground_ratio=bottom_band_ratio,
        middle_band_foreground_ratio=middle_band_ratio,
        edge_density=edge_density,
        horizontal_band_peak_ratio=peak_ratio,
    )

    issues: List[FrameHeuristicIssue] = []

    # 1) Border crowding.
    border_score = border_foreground_ratio / (foreground_ratio + 1e-6) if foreground_ratio > 0 else 0.0
    if foreground_ratio > 0.01 and border_score > 0.34:
        issues.append(
            FrameHeuristicIssue(
                code="border_crowding",
                score=min(1.0, border_score),
                message="Foreground content is heavily concentrated near frame borders.",
            )
        )

    # 2) Top/bottom dark band imbalance relative to center occupancy.
    top_bottom_mean = (top_band_ratio + bottom_band_ratio) / 2.0
    if foreground_ratio > 0.06 and middle_band_ratio > 0.06 and top_bottom_mean < (middle_band_ratio * 0.22):
        imbalance = middle_band_ratio / (top_bottom_mean + 1e-6)
        issues.append(
            FrameHeuristicIssue(
                code="top_bottom_empty_imbalance",
                score=min(1.0, imbalance / 6.0),
                message="Top/bottom bands appear underused relative to center text/object occupancy.",
            )
        )

    # 3) Dense horizontal label-like bands near likely x-axis/label region.
    # Be conservative here: stacked centered equations in formula-only scenes can
    # create repeated horizontal edge rows without actually being crowded axis labels.
    border_score = border_foreground_ratio / (foreground_ratio + 1e-6) if foreground_ratio > 0 else 0.0
    healthy_margins = border_score < 0.24 and foreground_ratio < 0.30
    has_strong_band = peak > baseline + 1.4 * spread and peak_ratio > 1.6 and max_high_run >= 4
    centered_content = middle_band_ratio > top_band_ratio * 1.35 and middle_band_ratio > bottom_band_ratio * 1.35
    formula_like_center_stack = (
        healthy_margins
        and centered_content
        and lower_vs_middle_peak_ratio < 1.7
        and bottom_band_ratio < middle_band_ratio * 0.72
    )
    context_support = (
        lower_vs_middle_peak_ratio > 1.45
        or border_score > 0.2
        or bottom_band_ratio > middle_band_ratio * 0.72
    )
    if (
        edge_density > 0.01
        and has_strong_band
        and context_support
        and not formula_like_center_stack
        and not (healthy_margins and lower_vs_middle_peak_ratio < 1.45)
    ):
        issues.append(
            FrameHeuristicIssue(
                code="dense_horizontal_label_band",
                score=min(1.0, max(peak_ratio / 6.0, lower_vs_middle_peak_ratio / 3.0)),
                message="A dense horizontal detail band suggests crowded labels near an axis region.",
            )
        )

    return {
        "metrics": metrics.to_dict(),
        "issues": [issue.to_dict() for issue in issues],
    }


class PreviewQAService:
    """
    Render and evaluate preview video quality for generated Manim scenes.
    """

    def __init__(self, manim_generator=None, ffmpeg_path: Optional[str] = None):
        self.manim_generator = manim_generator
        self.ffmpeg_path = ffmpeg_path or settings.ffmpeg_path

    def run_preview_qa(
        self,
        script_content: str,
        scene_name: str = "GeneratedScene",
        sample_points: Optional[Sequence[float]] = None,
    ) -> Dict[str, object]:
        """
        Render low-quality preview, sample frames, run heuristics, return report.
        """
        points = list(sample_points) if sample_points else [0.12, 0.38, 0.62, 0.88]
        work_dir = Path(tempfile.mkdtemp(prefix="preview_qa_"))
        report: Dict[str, object] = {
            "ok": False,
            "stage": "initializing",
            "preview_video_path": None,
            "frame_paths": [],
            "frames": [],
            "summary": {},
            "errors": [],
        }

        temp_script_path: Optional[Path] = None
        try:
            report["stage"] = "rendering_preview"
            converted_script = convert_manim_code(script_content)
            temp_script_path = work_dir / "preview_scene.py"
            temp_script_path.write_text(converted_script, encoding="utf-8")

            output_name = f"preview_{uuid.uuid4().hex[:10]}"
            preview_video_path = self._render_preview_video(
                script_path=temp_script_path,
                scene_name=scene_name,
                output_name=output_name,
            )
            if not preview_video_path:
                report["errors"].append("preview_render_failed")
                return report
            report["preview_video_path"] = str(preview_video_path)

            report["stage"] = "extracting_frames"
            frame_dir = work_dir / "frames"
            frame_dir.mkdir(parents=True, exist_ok=True)
            frame_paths = self._extract_sample_frames(preview_video_path, frame_dir, points)
            report["frame_paths"] = [str(path) for path in frame_paths]
            if not frame_paths:
                report["errors"].append("frame_extraction_failed")
                return report

            report["stage"] = "analyzing_frames"
            frames_payload: List[Dict[str, object]] = []
            issue_to_frames: Dict[str, List[int]] = {}
            issue_peak_scores: Dict[str, float] = {}

            for idx, frame_path in enumerate(frame_paths):
                frame_rgb = np.array(Image.open(frame_path).convert("RGB"))
                analysis = analyze_frame_heuristics(frame_rgb)
                frame_issues = analysis["issues"]

                frames_payload.append(
                    {
                        "index": idx,
                        "sample_point": points[idx] if idx < len(points) else None,
                        "path": str(frame_path),
                        "metrics": analysis["metrics"],
                        "issues": frame_issues,
                    }
                )

                for issue in frame_issues:
                    code = str(issue["code"])
                    score = float(issue["score"])
                    issue_to_frames.setdefault(code, []).append(idx)
                    issue_peak_scores[code] = max(issue_peak_scores.get(code, 0.0), score)

            aggregate_issues = []
            for code, frame_ids in issue_to_frames.items():
                aggregate_issues.append(
                    {
                        "code": code,
                        "frames": frame_ids,
                        "frame_count": len(frame_ids),
                        "peak_score": round(issue_peak_scores.get(code, 0.0), 4),
                    }
                )

            total_issue_hits = sum(len(frame["issues"]) for frame in frames_payload)
            has_blocking_issue = any(
                issue["frame_count"] >= max(2, len(frame_paths) // 2)
                for issue in aggregate_issues
            )

            report["frames"] = frames_payload
            report["summary"] = {
                "frames_analyzed": len(frame_paths),
                "sample_points": points,
                "total_issue_hits": total_issue_hits,
                "aggregate_issues": aggregate_issues,
                "has_blocking_issue": has_blocking_issue,
            }
            report["ok"] = not has_blocking_issue
            report["stage"] = "complete"
            return report
        except Exception as exc:
            logger.exception("Preview QA pipeline failed: %s", exc)
            report["errors"].append(str(exc))
            report["stage"] = "failed"
            return report
        finally:
            # Keep preview video (stored in Manim output path), cleanup scratch artifacts.
            if temp_script_path and temp_script_path.exists():
                try:
                    temp_script_path.unlink()
                except OSError:
                    pass
            shutil.rmtree(work_dir, ignore_errors=True)

    def _render_preview_video(self, script_path: Path, scene_name: str, output_name: str) -> Optional[Path]:
        if self.manim_generator is None:
            import sys

            sys.path.append(str(Path(__file__).parent.parent.parent.parent))
            from manim_video_generator import ManimVideoGenerator

            self.manim_generator = ManimVideoGenerator(
                output_dir=str(settings.video_output_path),
                manim_path=settings.manim_path,
            )

        video_path = self.manim_generator.generate_video(
            script_path=str(script_path),
            scene_name=scene_name,
            quality="low_quality",
            format="mp4",
            output_name=output_name,
        )
        return Path(video_path) if video_path else None

    def _resolve_ffmpeg_path(self) -> str:
        configured = self.ffmpeg_path
        if configured and os.path.exists(configured):
            return configured
        detected = shutil.which("ffmpeg")
        if detected:
            return detected
        raise RuntimeError("ffmpeg executable not found")

    def _resolve_ffprobe_path(self) -> str:
        ffprobe_candidate = str(Path(self._resolve_ffmpeg_path()).with_name("ffprobe"))
        if os.path.exists(ffprobe_candidate):
            return ffprobe_candidate
        detected = shutil.which("ffprobe")
        if detected:
            return detected
        raise RuntimeError("ffprobe executable not found")

    def _video_duration_seconds(self, video_path: Path) -> float:
        ffprobe_path = self._resolve_ffprobe_path()
        cmd = [
            ffprobe_path,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "json",
            str(video_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        payload = json.loads(result.stdout or "{}")
        duration = float(payload.get("format", {}).get("duration", 0.0))
        if duration <= 0:
            raise RuntimeError("Unable to determine preview video duration")
        return duration

    def _extract_sample_frames(
        self,
        video_path: Path,
        frame_dir: Path,
        sample_points: Sequence[float],
    ) -> List[Path]:
        ffmpeg = self._resolve_ffmpeg_path()
        duration = self._video_duration_seconds(video_path)
        frame_paths: List[Path] = []

        for index, point in enumerate(sample_points):
            clamped = min(0.98, max(0.02, float(point)))
            timestamp = duration * clamped
            frame_path = frame_dir / f"frame_{index:02d}.png"
            cmd = [
                ffmpeg,
                "-ss",
                f"{timestamp:.3f}",
                "-i",
                str(video_path),
                "-frames:v",
                "1",
                "-q:v",
                "2",
                "-y",
                str(frame_path),
            ]
            subprocess.run(cmd, capture_output=True, text=True, check=True)
            if frame_path.exists():
                frame_paths.append(frame_path)

        return frame_paths
