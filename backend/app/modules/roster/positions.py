"""Controlled football position codes and provider-label normalization."""

from typing import Literal, cast


PositionCode = Literal["GK", "RB", "CB", "LB", "DM", "CM", "AM", "RW", "LW", "ST", "OTHER"]
POSITION_CODES: tuple[PositionCode, ...] = (
    "GK", "RB", "CB", "LB", "DM", "CM", "AM", "RW", "LW", "ST", "OTHER"
)

_ALIASES: dict[str, PositionCode] = {
    "goalkeeper": "GK",
    "keeper": "GK",
    "gk": "GK",
    "right back": "RB",
    "right-back": "RB",
    "rb": "RB",
    "defender": "CB",
    "centre back": "CB",
    "center back": "CB",
    "cb": "CB",
    "left back": "LB",
    "left-back": "LB",
    "lb": "LB",
    "defensive midfielder": "DM",
    "dm": "DM",
    "midfielder": "CM",
    "central midfielder": "CM",
    "cm": "CM",
    "attacking midfielder": "AM",
    "am": "AM",
    "right winger": "RW",
    "rw": "RW",
    "left winger": "LW",
    "lw": "LW",
    "attacker": "ST",
    "forward": "ST",
    "striker": "ST",
    "st": "ST",
    "other": "OTHER",
}


def normalize_position(value: str | None) -> PositionCode:
    if value is None:
        return "OTHER"
    normalized = " ".join(value.strip().lower().split())
    if normalized.upper() in POSITION_CODES:
        return cast(PositionCode, normalized.upper())
    return _ALIASES.get(normalized, "OTHER")
