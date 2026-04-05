from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.vertical_video import (  # noqa: E402
    ContentFamily,
    DerivationSpec,
    DerivationStep,
    DurationBucket,
    GraphSample,
    GraphSpec,
    KinematicsSpec,
    MotionPhase,
    VerticalVideoRequest,
    VerticalVideoService,
)


OUTPUT_DIR = ROOT / "artifacts" / "vertical_video"


def build_requests() -> list[tuple[str, VerticalVideoRequest]]:
    return [
        (
            "physics_projectile_demo",
            VerticalVideoRequest(
                topic="Projectile motion",
                family=ContentFamily.PHYSICS,
                goal="show how vx stays horizontal while vy changes",
                duration_bucket=DurationBucket.MEDIUM,
                kinematics=KinematicsSpec(
                    equation_text="y = x - 0.12x^2",
                    trajectory_expression="x - 0.12*x**2",
                    phases=(
                        MotionPhase("Launch", 1.0, 3.0, 2.5),
                        MotionPhase("Mid-flight", 1.0, 3.0, 0.7),
                        MotionPhase("Descent", 1.0, 3.0, -1.3),
                    ),
                ),
            ),
        ),
        (
            "math_parabola_graph_demo",
            VerticalVideoRequest(
                topic="How a parabola bends",
                family=ContentFamily.MATH,
                goal="explain the shape of y = x^2",
                duration_bucket=DurationBucket.LONG,
                graph=GraphSpec(
                    expression="x**2",
                    x_range=(-2.0, 2.0),
                    y_range=(0.0, 4.0),
                    samples=(
                        GraphSample(-1.0, 1.0, "left"),
                        GraphSample(0.0, 0.0, "vertex"),
                        GraphSample(2.0, 4.0, "right"),
                    ),
                    highlight_label="vertex",
                ),
            ),
        ),
        (
            "math_identity_derivation_demo",
            VerticalVideoRequest(
                topic="Expand (a+b)^2",
                family=ContentFamily.MATH,
                goal="show the derivation clearly",
                duration_bucket=DurationBucket.SHORT,
                derivation=DerivationSpec(
                    input_expression="(a+b)^2",
                    steps=(
                        DerivationStep("(a+b)^2"),
                        DerivationStep("(a+b)(a+b)"),
                        DerivationStep("a^2 + ab + ab + b^2"),
                        DerivationStep("a^2 + 2ab + b^2", highlight="result"),
                    ),
                    final_expression="a^2 + 2ab + b^2",
                ),
            ),
        ),
    ]


def main() -> None:
    service = VerticalVideoService()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for output_name, request in build_requests():
        mp4_path = service.render_video(
            request=request,
            output_dir=OUTPUT_DIR / output_name,
            output_name=output_name,
            quality="l",
        )
        print(f"rendered {output_name}: {mp4_path}")


if __name__ == "__main__":
    main()
