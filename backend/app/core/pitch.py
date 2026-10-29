"""Generate a sample StatX Analytics football pitch visualization."""

from pathlib import Path

import matplotlib.pyplot as plt
from mplsoccer import Pitch


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "data" / "exports" / "test_pitch.png"


def generate_test_pitch(output_path: Path | str = DEFAULT_OUTPUT_PATH) -> Path:
    """Draw a dark football pitch with three fictional shots and save it.

    Args:
        output_path: Destination of the generated PNG image.

    Returns:
        The absolute path of the saved image.
    """
    destination = Path(output_path).expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)

    pitch = Pitch(
        pitch_type="statsbomb",
        pitch_color="#0F2D1A",
        line_color="#4ADE80",
        linewidth=2,
        goal_type="box",
    )
    figure, axis = pitch.draw(
        figsize=(12, 8),
        tight_layout=False,
        constrained_layout=True,
    )
    figure.set_facecolor("#0F2D1A")

    shots = (
        {"x": 108, "y": 40, "color": "#22C55E", "label": "But"},
        {"x": 101, "y": 31, "color": "#EF4444", "label": "Tir raté"},
        {"x": 96, "y": 50, "color": "#EF4444", "label": "Tir raté"},
    )

    displayed_labels: set[str] = set()
    for shot in shots:
        label = str(shot["label"])
        pitch.scatter(
            float(shot["x"]),
            float(shot["y"]),
            s=260,
            c=str(shot["color"]),
            edgecolors="white",
            linewidth=1.5,
            alpha=0.95,
            label=label if label not in displayed_labels else None,
            ax=axis,
            zorder=3,
        )
        displayed_labels.add(label)

    axis.set_title(
        "StatX Analytics — Carte de tirs (démonstration)",
        color="white",
        fontsize=16,
        fontweight="bold",
        pad=16,
    )
    legend = axis.legend(
        loc="lower left",
        facecolor="#0F2D1A",
        edgecolor="#4ADE80",
        labelcolor="white",
        framealpha=0.9,
    )
    legend.get_frame().set_linewidth(1)

    figure.savefig(
        destination,
        dpi=180,
        bbox_inches="tight",
        facecolor=figure.get_facecolor(),
    )
    plt.close(figure)
    return destination


if __name__ == "__main__":
    generated_file = generate_test_pitch()
    print(f"Terrain de test généré : {generated_file}")

