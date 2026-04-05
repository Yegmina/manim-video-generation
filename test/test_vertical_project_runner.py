from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from vertical_project_runner import VerticalProjectRunner, create_seed_state


def _make_runner(tmp_path: Path) -> VerticalProjectRunner:
    state_dir = tmp_path / "project_state" / "vertical_video"
    create_seed_state(state_dir)
    return VerticalProjectRunner(state_dir)


def test_seed_state_sets_expected_initial_next_task(tmp_path: Path):
    runner = _make_runner(tmp_path)

    next_task = runner.next_task()

    assert next_task is not None
    assert next_task["id"] == "scene-manifest-emission"
    assert runner.status()["phase"] == "scaffolded-subsystem-with-durable-runner"


def test_start_and_complete_task_updates_status_and_artifacts(tmp_path: Path):
    runner = _make_runner(tmp_path)

    created_artifact = tmp_path / "manifest.json"
    created_artifact.write_text("{}", encoding="utf-8")

    started = runner.start_task("scene-manifest-emission", note="starting manifest work")
    assert started["status"] == "in_progress"
    assert runner.status()["current_task_id"] == "scene-manifest-emission"

    completed = runner.complete_task(
        "scene-manifest-emission",
        note="manifest emission implemented",
        artifact_specs=[
            {
                "path": str(created_artifact),
                "kind": "report",
                "description": "example manifest artifact",
            }
        ],
    )

    assert completed["status"] == "done"
    assert runner.status()["current_task_id"] is None
    artifacts = runner.artifacts()["artifacts"]
    assert artifacts[-1]["path"] == str(created_artifact)
    assert artifacts[-1]["source_task_id"] == "scene-manifest-emission"
    assert artifacts[-1]["exists"] is True


def test_next_task_respects_dependencies(tmp_path: Path):
    runner = _make_runner(tmp_path)

    runner.start_task("scene-manifest-emission")
    runner.complete_task("scene-manifest-emission", note="done")

    next_task = runner.next_task()

    assert next_task is not None
    assert next_task["id"] in {"math-template-happy-path", "semantic-benchmark-integration"}
    ready_ids = [task["id"] for task in runner.list_ready_tasks()]
    assert "semantic-benchmark-integration" in ready_ids


def test_summary_mentions_recent_work_and_progress(tmp_path: Path):
    runner = _make_runner(tmp_path)

    runner.log("checked current planner/service scaffold")
    summary = runner.summary_text()

    assert "StudyShorts-style vertical video replacement" in summary
    assert "Artifacts tracked:" in summary
    assert "checked current planner/service scaffold" in summary


def test_seed_files_are_machine_readable(tmp_path: Path):
    state_dir = tmp_path / "project_state" / "vertical_video"
    create_seed_state(state_dir)

    status = json.loads((state_dir / "status.json").read_text(encoding="utf-8"))
    backlog = json.loads((state_dir / "backlog.json").read_text(encoding="utf-8"))
    artifacts = json.loads((state_dir / "artifacts.json").read_text(encoding="utf-8"))
    worklog_lines = (state_dir / "worklog.jsonl").read_text(encoding="utf-8").strip().splitlines()

    assert status["state_version"] == 1
    assert backlog["tasks"][0]["id"] == "runner-bootstrap"
    assert artifacts["artifacts"][0]["path"] == "docs/vertical-video-system.md"
    assert len(worklog_lines) >= 2
