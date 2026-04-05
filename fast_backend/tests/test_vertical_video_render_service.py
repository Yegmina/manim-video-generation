from pathlib import Path

from app.vertical_video import ContentFamily, VerticalVideoRequest, VerticalVideoService


def test_render_video_writes_script_and_returns_matching_mp4(tmp_path, monkeypatch):
    service = VerticalVideoService()
    request = VerticalVideoRequest(
        topic="Projectile motion",
        family=ContentFamily.PHYSICS,
        goal="show the curve",
    )

    created = {}

    def fake_run(command, check):
        assert check is True
        assert command[:4] == ["python", "-m", "manim", "render"]
        media_dir = Path(command[command.index("--media_dir") + 1])
        output_name = command[command.index("-o") + 1]
        output_path = media_dir / "videos" / "GeneratedScene" / f"{output_name}.mp4"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"fake-mp4")
        created["path"] = output_path

    monkeypatch.setattr("app.vertical_video.service.subprocess.run", fake_run)

    result = service.render_video(request, output_dir=tmp_path, output_name="physics_demo")

    assert result == created["path"]
    assert (tmp_path / "scripts" / "physics_demo.py").exists()
