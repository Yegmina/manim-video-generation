from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


DEFAULT_STATE_DIR = Path("project_state/vertical_video")
VALID_STATUSES = {"todo", "in_progress", "blocked", "done"}
PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class StateError(RuntimeError):
    pass


@dataclass
class RunnerState:
    root: Path
    status_path: Path
    backlog_path: Path
    worklog_path: Path
    artifacts_path: Path

    @classmethod
    def open(cls, root: Path) -> "RunnerState":
        root = root.resolve()
        return cls(
            root=root,
            status_path=root / "status.json",
            backlog_path=root / "backlog.json",
            worklog_path=root / "worklog.jsonl",
            artifacts_path=root / "artifacts.json",
        )

    def ensure_exists(self) -> None:
        missing = [
            path.name
            for path in [self.status_path, self.backlog_path, self.worklog_path, self.artifacts_path]
            if not path.exists()
        ]
        if missing:
            raise StateError(
                f"State directory {self.root} is missing required files: {', '.join(missing)}"
            )

    def read_json(self, path: Path) -> Any:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def write_json(self, path: Path, payload: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
            handle.write("\n")

    def read_status(self) -> Dict[str, Any]:
        return self.read_json(self.status_path)

    def write_status(self, payload: Dict[str, Any]) -> None:
        self.write_json(self.status_path, payload)

    def read_backlog(self) -> Dict[str, Any]:
        return self.read_json(self.backlog_path)

    def write_backlog(self, payload: Dict[str, Any]) -> None:
        self.write_json(self.backlog_path, payload)

    def read_artifacts(self) -> Dict[str, Any]:
        return self.read_json(self.artifacts_path)

    def write_artifacts(self, payload: Dict[str, Any]) -> None:
        self.write_json(self.artifacts_path, payload)

    def append_worklog(self, entry: Dict[str, Any]) -> None:
        self.worklog_path.parent.mkdir(parents=True, exist_ok=True)
        with self.worklog_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def read_worklog(self) -> List[Dict[str, Any]]:
        if not self.worklog_path.exists():
            return []
        entries: List[Dict[str, Any]] = []
        with self.worklog_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
        return entries


class VerticalProjectRunner:
    def __init__(self, state_dir: Path = DEFAULT_STATE_DIR):
        self.state = RunnerState.open(state_dir)
        self.state.ensure_exists()

    def status(self) -> Dict[str, Any]:
        return self.state.read_status()

    def backlog(self) -> Dict[str, Any]:
        return self.state.read_backlog()

    def artifacts(self) -> Dict[str, Any]:
        return self.state.read_artifacts()

    def worklog(self) -> List[Dict[str, Any]]:
        return self.state.read_worklog()

    def list_ready_tasks(self) -> List[Dict[str, Any]]:
        backlog = self.backlog()
        tasks = backlog["tasks"]
        done_ids = {task["id"] for task in tasks if task["status"] == "done"}
        in_progress = [task for task in tasks if task["status"] == "in_progress"]
        if in_progress:
            return in_progress

        ready: List[Dict[str, Any]] = []
        for index, task in enumerate(tasks):
            if task["status"] != "todo":
                continue
            deps = task.get("depends_on", [])
            if all(dep in done_ids for dep in deps):
                decorated = dict(task)
                decorated["_order"] = index
                ready.append(decorated)
        ready.sort(key=lambda item: (PRIORITY_ORDER.get(item.get("priority", "medium"), 99), item["_order"]))
        for task in ready:
            task.pop("_order", None)
        return ready

    def next_task(self) -> Optional[Dict[str, Any]]:
        ready = self.list_ready_tasks()
        return ready[0] if ready else None

    def _find_task(self, task_id: str) -> Dict[str, Any]:
        backlog = self.backlog()
        for task in backlog["tasks"]:
            if task["id"] == task_id:
                return task
        raise StateError(f"Unknown task id: {task_id}")

    def _write_event(self, event_type: str, message: str, **extra: Any) -> Dict[str, Any]:
        entry = {"timestamp": utc_now(), "event": event_type, "message": message, **extra}
        self.state.append_worklog(entry)
        return entry

    def start_task(self, task_id: str, note: Optional[str] = None) -> Dict[str, Any]:
        backlog = self.backlog()
        status = self.status()

        chosen = None
        for task in backlog["tasks"]:
            if task["id"] == task_id:
                chosen = task
                break
        if chosen is None:
            raise StateError(f"Unknown task id: {task_id}")
        if chosen["status"] == "done":
            raise StateError(f"Task {task_id} is already done")

        done_ids = {task["id"] for task in backlog["tasks"] if task["status"] == "done"}
        unmet = [dep for dep in chosen.get("depends_on", []) if dep not in done_ids]
        if unmet:
            raise StateError(f"Task {task_id} has unmet dependencies: {', '.join(unmet)}")

        for task in backlog["tasks"]:
            if task["status"] == "in_progress" and task["id"] != task_id:
                task["status"] = "todo"
                task.pop("started_at", None)

        chosen["status"] = "in_progress"
        chosen["started_at"] = utc_now()
        chosen.pop("completed_at", None)
        self.state.write_backlog(backlog)

        status["current_task_id"] = task_id
        status["current_task_title"] = chosen["title"]
        status["updated_at"] = utc_now()
        status["last_resumed_at"] = status["updated_at"]
        if note:
            status["latest_note"] = note
        self.state.write_status(status)

        self._write_event("task_started", note or f"Started {task_id}", task_id=task_id, title=chosen["title"])
        return chosen

    def complete_task(
        self,
        task_id: str,
        note: str,
        artifact_specs: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        backlog = self.backlog()
        status = self.status()

        chosen = None
        for task in backlog["tasks"]:
            if task["id"] == task_id:
                chosen = task
                break
        if chosen is None:
            raise StateError(f"Unknown task id: {task_id}")

        chosen["status"] = "done"
        chosen["completed_at"] = utc_now()
        self.state.write_backlog(backlog)

        if artifact_specs:
            for spec in artifact_specs:
                self.record_artifact(
                    path=spec["path"],
                    kind=spec.get("kind", "file"),
                    description=spec.get("description", ""),
                    source_task_id=task_id,
                )

        if status.get("current_task_id") == task_id:
            status["current_task_id"] = None
            status["current_task_title"] = None
        status["updated_at"] = utc_now()
        status["latest_note"] = note
        self.state.write_status(status)

        self._write_event("task_completed", note, task_id=task_id, title=chosen["title"])
        return chosen

    def record_artifact(
        self,
        path: str,
        kind: str,
        description: str,
        source_task_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        artifact_index = self.artifacts()
        artifact_id = f"artifact-{len(artifact_index['artifacts']) + 1:03d}"
        repo_path = Path(path)
        artifact = {
            "id": artifact_id,
            "path": path,
            "kind": kind,
            "description": description,
            "source_task_id": source_task_id,
            "recorded_at": utc_now(),
            "exists": repo_path.exists(),
        }
        artifact_index["artifacts"].append(artifact)
        artifact_index["updated_at"] = artifact["recorded_at"]
        self.state.write_artifacts(artifact_index)
        self._write_event(
            "artifact_recorded",
            f"Recorded artifact {path}",
            artifact_id=artifact_id,
            path=path,
            source_task_id=source_task_id,
        )
        return artifact

    def log(self, message: str) -> Dict[str, Any]:
        status = self.status()
        status["updated_at"] = utc_now()
        status["latest_note"] = message
        self.state.write_status(status)
        return self._write_event(
            "note",
            message,
            current_task_id=status.get("current_task_id"),
        )

    def summary_text(self) -> str:
        status = self.status()
        backlog = self.backlog()
        artifacts = self.artifacts()
        worklog = self.worklog()
        tasks = backlog["tasks"]
        done = [task for task in tasks if task["status"] == "done"]
        in_progress = [task for task in tasks if task["status"] == "in_progress"]
        blocked = [task for task in tasks if task["status"] == "blocked"]
        next_task = self.next_task()
        recent = worklog[-3:]

        lines = [
            f"Project: {status['project_name']}",
            f"Phase: {status['phase']}",
            f"Mission: {status['mission']}",
            f"Current task: {status.get('current_task_title') or 'none'}",
            f"Progress: {len(done)}/{len(tasks)} tasks done, {len(in_progress)} in progress, {len(blocked)} blocked",
            f"Artifacts tracked: {len(artifacts['artifacts'])}",
            f"Next recommended task: {(next_task['id'] + ' - ' + next_task['title']) if next_task else 'none'}",
        ]
        if recent:
            lines.append("Recent worklog:")
            for entry in recent:
                lines.append(f"- {entry['timestamp']}: {entry['message']}")
        return "\n".join(lines)


def create_seed_state(state_dir: Path = DEFAULT_STATE_DIR) -> None:
    state = RunnerState.open(state_dir)
    state.root.mkdir(parents=True, exist_ok=True)

    now = utc_now()
    state.write_status(
        {
            "project_name": "StudyShorts-style vertical video replacement",
            "project_slug": "vertical-video-replacement",
            "mission": "Build a deterministic, testable, portrait-first video generation subsystem that can replace brittle prompt-only generation for short math and physics explainers.",
            "phase": "scaffolded-subsystem-with-durable-runner",
            "focus": "Resume from durable state, then push scene-manifest + semantic-validation integration.",
            "current_task_id": None,
            "current_task_title": None,
            "latest_note": "Durable long-horizon runner initialized.",
            "updated_at": now,
            "last_resumed_at": now,
            "state_version": 1,
        }
    )

    state.write_backlog(
        {
            "updated_at": now,
            "tasks": [
                {
                    "id": "runner-bootstrap",
                    "title": "Add durable runner/state scaffolding for the vertical-video project",
                    "status": "done",
                    "priority": "high",
                    "area": "workflow",
                    "depends_on": [],
                    "notes": "Adds resumable status/backlog/worklog/artifact tracking inside the repo.",
                    "completed_at": now,
                },
                {
                    "id": "scene-manifest-emission",
                    "title": "Emit machine-readable scene manifests from generated vertical scenes",
                    "status": "todo",
                    "priority": "high",
                    "area": "validation",
                    "depends_on": [],
                    "notes": "Needed so semantic validation runs against measured scene metadata instead of hand-authored contracts.",
                },
                {
                    "id": "semantic-benchmark-integration",
                    "title": "Run semantic validation inside the robustness benchmark flow",
                    "status": "todo",
                    "priority": "high",
                    "area": "validation",
                    "depends_on": ["scene-manifest-emission"],
                    "notes": "Connect manifest-aware checks into benchmark scoring and reports.",
                },
                {
                    "id": "plan-preview-api",
                    "title": "Expose a plan-preview API for the vertical-video subsystem",
                    "status": "todo",
                    "priority": "medium",
                    "area": "api",
                    "depends_on": [],
                    "notes": "Useful before full render job wiring; should preview structured plans and emitted scripts.",
                },
                {
                    "id": "math-template-happy-path",
                    "title": "Implement a strong math derivation happy-path example with tests",
                    "status": "todo",
                    "priority": "high",
                    "area": "templates",
                    "depends_on": [],
                    "notes": "The kickoff doc explicitly called out math_derivation_stack as a next milestone.",
                },
                {
                    "id": "physics-regression-fixtures",
                    "title": "Expand physics examples and add render/QA regression fixtures",
                    "status": "todo",
                    "priority": "medium",
                    "area": "templates",
                    "depends_on": [],
                    "notes": "Build on the projectile example and keep portrait quality stable over time.",
                },
            ],
        }
    )

    state.worklog_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "timestamp": now,
                        "event": "seeded",
                        "message": "Initialized durable runner state for the vertical-video replacement effort.",
                    }
                ),
                json.dumps(
                    {
                        "timestamp": now,
                        "event": "seeded",
                        "message": "Captured existing subsystem docs and implementation files as starting artifacts.",
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    state.write_artifacts(
        {
            "updated_at": now,
            "artifacts": [
                {
                    "id": "artifact-001",
                    "path": "docs/vertical-video-system.md",
                    "kind": "design-doc",
                    "description": "Kickoff architecture for the deterministic vertical-video subsystem.",
                    "source_task_id": None,
                    "recorded_at": now,
                    "exists": (Path("docs/vertical-video-system.md")).exists(),
                },
                {
                    "id": "artifact-002",
                    "path": "VALIDATION_KICKOFF.md",
                    "kind": "design-doc",
                    "description": "Semantic-validation direction and gap analysis for the replacement system.",
                    "source_task_id": None,
                    "recorded_at": now,
                    "exists": (Path("VALIDATION_KICKOFF.md")).exists(),
                },
                {
                    "id": "artifact-003",
                    "path": "fast_backend/app/vertical_video",
                    "kind": "code-dir",
                    "description": "Current deterministic planner/service/models/builder scaffold for vertical videos.",
                    "source_task_id": None,
                    "recorded_at": now,
                    "exists": (Path("fast_backend/app/vertical_video")).exists(),
                },
                {
                    "id": "artifact-004",
                    "path": "fast_backend/tests/test_vertical_video_examples.py",
                    "kind": "test",
                    "description": "Current projectile example coverage for the vertical-video subsystem.",
                    "source_task_id": None,
                    "recorded_at": now,
                    "exists": (Path("fast_backend/tests/test_vertical_video_examples.py")).exists(),
                },
                {
                    "id": "artifact-005",
                    "path": "vertical_project_runner.py",
                    "kind": "tool",
                    "description": "CLI + library entrypoint for durable continuation/resume state handling.",
                    "source_task_id": "runner-bootstrap",
                    "recorded_at": now,
                    "exists": (Path("vertical_project_runner.py")).exists(),
                },
                {
                    "id": "artifact-006",
                    "path": "docs/long-horizon-runner.md",
                    "kind": "doc",
                    "description": "Operator notes for resuming and updating the vertical-video project state.",
                    "source_task_id": "runner-bootstrap",
                    "recorded_at": now,
                    "exists": (Path("docs/long-horizon-runner.md")).exists(),
                },
            ],
        }
    )


def parse_artifact_args(items: Optional[List[str]]) -> List[Dict[str, str]]:
    parsed: List[Dict[str, str]] = []
    for item in items or []:
        parts = item.split(":", 2)
        if len(parts) != 3:
            raise StateError(
                "Artifact arguments must use path:kind:description format"
            )
        path, kind, description = parts
        parsed.append({"path": path, "kind": kind, "description": description})
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Durable runner for the vertical-video replacement project")
    parser.add_argument("--state-dir", default=str(DEFAULT_STATE_DIR), help="Path to the state directory")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("summary", help="Print a concise project summary")
    subparsers.add_parser("next", help="Print the next recommended task as JSON")
    subparsers.add_parser("seed", help="Create or overwrite the seeded project state")

    start = subparsers.add_parser("start", help="Mark a task as in progress")
    start.add_argument("task_id")
    start.add_argument("--note")

    complete = subparsers.add_parser("complete", help="Mark a task as done")
    complete.add_argument("task_id")
    complete.add_argument("--note", required=True)
    complete.add_argument(
        "--artifact",
        action="append",
        help="Artifact spec in path:kind:description format; may be repeated",
    )

    log_cmd = subparsers.add_parser("log", help="Append a worklog note")
    log_cmd.add_argument("message")

    artifact = subparsers.add_parser("artifact", help="Record an artifact")
    artifact.add_argument("path")
    artifact.add_argument("kind")
    artifact.add_argument("description")
    artifact.add_argument("--task-id")

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    state_dir = Path(args.state_dir)

    try:
        if args.command == "seed":
            create_seed_state(state_dir)
            print(f"Seeded durable project state at {state_dir}")
            return 0

        runner = VerticalProjectRunner(state_dir)

        if args.command == "summary":
            print(runner.summary_text())
            return 0

        if args.command == "next":
            print(json.dumps(runner.next_task(), indent=2))
            return 0

        if args.command == "start":
            task = runner.start_task(args.task_id, note=args.note)
            print(json.dumps(task, indent=2))
            return 0

        if args.command == "complete":
            task = runner.complete_task(
                args.task_id,
                note=args.note,
                artifact_specs=parse_artifact_args(args.artifact),
            )
            print(json.dumps(task, indent=2))
            return 0

        if args.command == "log":
            entry = runner.log(args.message)
            print(json.dumps(entry, indent=2))
            return 0

        if args.command == "artifact":
            artifact = runner.record_artifact(
                path=args.path,
                kind=args.kind,
                description=args.description,
                source_task_id=args.task_id,
            )
            print(json.dumps(artifact, indent=2))
            return 0

        parser.error(f"Unknown command: {args.command}")
        return 2
    except StateError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
