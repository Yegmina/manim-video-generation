#!/usr/bin/env python3
"""Run deterministic vertical-video examples end to end."""

from __future__ import annotations

import argparse
import asyncio
import json
import shutil
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List

from fast_backend.app.services.llm_service import LLMService
from fast_backend.app.services.preview_qa_service import PreviewQAService
from fast_backend.app.services.semantic_validation import validate_scene_contract
from fast_backend.app.vertical_video import VerticalVideoService, builtin_vertical_examples, get_example
from manim_video_generator import ManimVideoGenerator


def _json_ready(value: Any) -> Any:
    if is_dataclass(value):
        return {key: _json_ready(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(item) for item in value]
    return value


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run deterministic vertical-video example renders.")
    parser.add_argument("--example", action="append", default=[], help="Example id to run. Repeatable. Defaults to all built-ins.")
    parser.add_argument("--quality", default="low_quality", help="Manim render quality preset.")
    parser.add_argument("--output-dir", default="scratch/vertical_examples", help="Directory for scripts and reports.")
    parser.add_argument("--report", default="scratch/vertical_examples/report.json", help="Summary report path.")
    parser.add_argument("--preview-qa", action="store_true", help="Render preview QA for each script.")
    parser.add_argument("--skip-render", action="store_true", help="Only build and validate scripts without final render.")
    return parser


async def _compile_validate(script: str) -> Dict[str, Any]:
    llm_service = LLMService()
    return await llm_service._validate_code_compilation(script)


def _selected_examples(example_ids: Iterable[str]):
    ids = list(example_ids)
    if ids:
        return [get_example(example_id) for example_id in ids]
    return builtin_vertical_examples()


def _copy_video_into_case_dir(video_path: str | None, case_dir: Path) -> str | None:
    if not video_path:
        return None
    source = Path(video_path)
    if not source.exists():
        return video_path
    target = case_dir / source.name
    if source.resolve() != target.resolve():
        shutil.copy2(source, target)
    return str(target)


async def _run_example(args: argparse.Namespace, example_id: str) -> Dict[str, Any]:
    spec = get_example(example_id)
    service = VerticalVideoService()
    plan = service.plan_video(spec.request)
    script = service.build_script_from_plan(plan)

    case_dir = Path(args.output_dir) / spec.example_id
    case_dir.mkdir(parents=True, exist_ok=True)
    script_path = case_dir / f"{spec.example_id}.py"
    plan_path = case_dir / f"{spec.example_id}_plan.json"
    semantic_path = case_dir / f"{spec.example_id}_semantic.json"
    script_path.write_text(script, encoding="utf-8")
    plan_path.write_text(json.dumps(_json_ready(plan), indent=2), encoding="utf-8")

    compile_validation = await _compile_validate(script)
    semantic_result = validate_scene_contract(spec.contract)
    semantic_payload = {
        "ok": semantic_result.ok,
        "issues": [asdict(issue) for issue in semantic_result.issues],
    }
    semantic_path.write_text(json.dumps(semantic_payload, indent=2), encoding="utf-8")

    preview_report = None
    preview_generator = None
    if args.preview_qa:
        try:
            preview_generator = ManimVideoGenerator(
                output_dir="fast_backend/generated_videos",
                manim_path="/home/openclaw/workspace/manim-video-generation/.venv/bin/python",
            )
            preview_service = PreviewQAService(manim_generator=preview_generator)
            preview_report = preview_service.run_preview_qa(script_content=script, scene_name="GeneratedScene")
        except Exception as exc:  # pragma: no cover - CLI/environment dependent
            preview_report = {
                "ok": False,
                "stage": "preview_unavailable",
                "errors": [str(exc)],
            }
        (case_dir / f"{spec.example_id}_preview.json").write_text(json.dumps(preview_report, indent=2), encoding="utf-8")

    rendered_video = None
    render_error = None
    if not args.skip_render:
        generator = preview_generator or ManimVideoGenerator(
            output_dir="fast_backend/generated_videos",
            manim_path="/home/openclaw/workspace/manim-video-generation/.venv/bin/python",
        )
        try:
            rendered_video = generator.generate_video(
                script_path=str(script_path),
                scene_name="GeneratedScene",
                quality=args.quality,
                output_name=spec.output_name,
            )
            rendered_video = _copy_video_into_case_dir(rendered_video, case_dir)
        except Exception as exc:  # pragma: no cover - defensive path for CLI use
            render_error = str(exc)

    result = {
        "example_id": spec.example_id,
        "expected_template": spec.expected_template,
        "template_id": plan.template_id,
        "template_matches": plan.template_id == spec.expected_template,
        "request": _json_ready(spec.request),
        "scene_spec": _json_ready(plan.scene_spec),
        "compile_validation": compile_validation,
        "semantic_validation": semantic_payload,
        "preview_qa": preview_report,
        "rendered_video": rendered_video,
        "render_error": render_error,
        "artifacts": {
            "script": str(script_path),
            "plan": str(plan_path),
            "semantic_report": str(semantic_path),
        },
    }
    return result


async def _run_all(args: argparse.Namespace) -> Dict[str, Any]:
    example_specs = _selected_examples(args.example)
    results: List[Dict[str, Any]] = []
    for spec in example_specs:
        results.append(await _run_example(args, spec.example_id))

    report = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "config": {
            "examples": [spec.example_id for spec in example_specs],
            "quality": args.quality,
            "preview_qa": bool(args.preview_qa),
            "skip_render": bool(args.skip_render),
        },
        "summary": {
            "total_examples": len(results),
            "rendered_examples": sum(1 for item in results if item.get("rendered_video")),
            "compile_passed": sum(1 for item in results if item["compile_validation"].get("success")),
            "semantic_passed": sum(1 for item in results if item["semantic_validation"].get("ok")),
        },
        "results": results,
    }
    return report


def main() -> int:
    parser = _build_arg_parser()
    args = parser.parse_args()

    report = asyncio.run(_run_all(args))
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"Wrote report to {report_path}")
    print(json.dumps(report["summary"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
