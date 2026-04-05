# Long-Horizon Runner for the Vertical-Video Project

This repo now has a small durable runner for the **StudyShorts-style vertical video replacement effort**.

## Why it exists

Detached coding runs are useful, but they do not leave behind a reliable project memory by themselves.
This runner gives the repo a lightweight source of truth for:

- current project status
- backlog and dependencies
- worklog/history
- tracked artifacts
- a repeatable way to resume work later

It is intentionally plain JSON + JSONL + one Python script. No database, no daemon, no hidden state.

## Files

State lives in:

- `project_state/vertical_video/status.json`
- `project_state/vertical_video/backlog.json`
- `project_state/vertical_video/worklog.jsonl`
- `project_state/vertical_video/artifacts.json`

Runner entrypoint:

- `vertical_project_runner.py`

## How resume/continuation works

1. A future worker runs `python vertical_project_runner.py summary`
   - gets the mission, phase, current task, progress, recent worklog, and next recommended task.
2. If a task should be resumed or claimed, run:
   - `python vertical_project_runner.py start <task-id> --note "what you are doing"`
3. While working, append meaningful notes:
   - `python vertical_project_runner.py log "implemented manifest schema draft"`
4. When output files or reports are produced, record them:
   - `python vertical_project_runner.py artifact path/to/file kind "what it is" --task-id <task-id>`
5. When a task is done:
   - `python vertical_project_runner.py complete <task-id> --note "what finished"`
   - optional artifacts can be attached at completion time too.

The runner determines the next task by:

- returning any currently `in_progress` task first
- otherwise choosing the highest-priority `todo` task whose dependencies are already done

That means future sessions can continue from repo state instead of reconstructing context from chat history.

## Commands

### Show summary

```bash
python vertical_project_runner.py summary
```

### Show next task as JSON

```bash
python vertical_project_runner.py next
```

### Start a task

```bash
python vertical_project_runner.py start scene-manifest-emission --note "begin manifest design"
```

### Add a worklog note

```bash
python vertical_project_runner.py log "mapped manifest fields to semantic validator inputs"
```

### Record an artifact

```bash
python vertical_project_runner.py artifact fast_backend/app/vertical_video/service.py code "service wiring changes" --task-id scene-manifest-emission
```

### Complete a task

```bash
python vertical_project_runner.py complete scene-manifest-emission \
  --note "scene manifests now emit measured metadata" \
  --artifact fast_backend/app/vertical_video/manifest.py:code:"manifest schema + helpers" \
  --artifact fast_backend/tests/test_vertical_manifest.py:test:"coverage for manifest emission"
```

### Re-seed the project state

```bash
python vertical_project_runner.py seed
```

Use `seed` only when you intentionally want to overwrite the tracked state with the repo's baseline seed.

## What is seeded today

The initial state reflects the repo's current replacement effort:

- deterministic vertical-video subsystem already exists under `fast_backend/app/vertical_video/`
- kickoff design docs already exist
- the durable runner itself is considered completed
- next recommended work is **scene manifest emission**, followed by semantic benchmark integration

## What this runner does not do

It does **not** automatically inspect git diffs, infer completed tasks, or watch filesystem changes.
Those are possible future extensions, but the current implementation stays explicit and reliable.
