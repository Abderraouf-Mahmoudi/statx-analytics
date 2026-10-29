"""Dark-themed football visualizations built with mplsoccer."""

from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from mplsoccer import Pitch


PITCH_COLOR = "#0F2D1A"
FIGURE_COLOR = "#111827"
LINE_COLOR = "#4ADE80"
GOAL_COLOR = "#22C55E"
MISS_COLOR = "#EF4444"


def _value(event: object, field: str, default: Any = None) -> Any:
    if isinstance(event, Mapping):
        return event.get(field, default)
    return getattr(event, field, default)


def _filtered_events(
    events: Iterable[object],
    event_type: str | None = None,
    player_id: int | None = None,
) -> list[object]:
    return [
        event
        for event in events
        if (event_type is None or _value(event, "type") == event_type)
        and (player_id is None or _value(event, "player_id") == player_id)
    ]


def _new_pitch(title: str) -> tuple[Pitch, plt.Figure, plt.Axes]:
    pitch = Pitch(
        pitch_type="statsbomb",
        pitch_color=PITCH_COLOR,
        line_color=LINE_COLOR,
        linewidth=1.8,
        goal_type="box",
    )
    figure, axis = pitch.draw(
        figsize=(12, 8),
        tight_layout=False,
        constrained_layout=True,
    )
    figure.set_facecolor(FIGURE_COLOR)
    axis.set_title(title, color="white", fontsize=16, fontweight="bold", pad=16)
    return pitch, figure, axis


def _save(figure: plt.Figure, output_path: Path | str) -> Path:
    destination = Path(output_path).expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(destination, dpi=180, bbox_inches="tight", facecolor=FIGURE_COLOR)
    plt.close(figure)
    return destination


def generate_shot_map(events: Iterable[object], output_path: Path | str) -> Path:
    """Generate a shot map sized by xG and colored by outcome."""
    shots = _filtered_events(events, event_type="shot")
    pitch, figure, axis = _new_pitch("Carte des tirs")

    for shot in shots:
        is_goal = str(_value(shot, "outcome", "")).lower() == "goal"
        xg = float(_value(shot, "xg_value", 0) or 0)
        pitch.scatter(
            float(_value(shot, "x_start")),
            float(_value(shot, "y_start")),
            s=100 + 900 * xg,
            c=GOAL_COLOR if is_goal else MISS_COLOR,
            edgecolors="white",
            linewidth=1.2,
            alpha=0.85,
            ax=axis,
            zorder=3,
        )

    legend = [
        Line2D([0], [0], marker="o", color="none", markerfacecolor=GOAL_COLOR, label="But", markersize=10),
        Line2D([0], [0], marker="o", color="none", markerfacecolor=MISS_COLOR, label="Tir raté", markersize=10),
    ]
    axis.legend(handles=legend, loc="lower left", facecolor=FIGURE_COLOR, labelcolor="white")
    if not shots:
        axis.text(60, 40, "Aucun tir enregistré", color="white", ha="center", va="center")
    return _save(figure, output_path)


def generate_pass_map(
    events: Iterable[object],
    player_id: int | None,
    output_path: Path | str,
) -> Path:
    """Generate a directional pass map for one player or the full match."""
    passes = _filtered_events(events, event_type="pass", player_id=player_id)
    pitch, figure, axis = _new_pitch(
        f"Carte des passes — joueur {player_id}" if player_id else "Carte des passes — match"
    )

    for pass_event in passes:
        successful = str(_value(pass_event, "outcome", "")).lower() in {
            "complete",
            "completed",
            "successful",
            "success",
        }
        pitch.arrows(
            float(_value(pass_event, "x_start")),
            float(_value(pass_event, "y_start")),
            float(_value(pass_event, "x_end")),
            float(_value(pass_event, "y_end")),
            color=GOAL_COLOR if successful else MISS_COLOR,
            width=1.7,
            headwidth=4,
            headlength=4,
            alpha=0.75,
            ax=axis,
            zorder=3,
        )

    if not passes:
        axis.text(60, 40, "Aucune passe enregistrée", color="white", ha="center", va="center")
    return _save(figure, output_path)


def generate_heatmap(
    events: Iterable[object],
    player_id: int | None,
    output_path: Path | str,
) -> Path:
    """Generate a KDE activity heatmap for one player or the full match."""
    activity = _filtered_events(events, player_id=player_id)
    pitch, figure, axis = _new_pitch(
        f"Carte de chaleur — joueur {player_id}" if player_id else "Carte de chaleur — match"
    )
    x = np.asarray([float(_value(event, "x_start")) for event in activity])
    y = np.asarray([float(_value(event, "y_start")) for event in activity])

    if len(activity) >= 3 and np.ptp(x) > 0 and np.ptp(y) > 0:
        pitch.kdeplot(
            x,
            y,
            ax=axis,
            fill=True,
            levels=80,
            thresh=0.05,
            cmap="magma",
            alpha=0.78,
            zorder=2,
        )
    elif activity:
        pitch.scatter(x, y, s=220, c="#F59E0B", alpha=0.7, ax=axis, zorder=3)
        axis.text(60, 4, "Données insuffisantes pour une estimation KDE", color="white", ha="center")
    else:
        axis.text(60, 40, "Aucune activité enregistrée", color="white", ha="center", va="center")
    return _save(figure, output_path)

