"""Explicitly download and warm the configured rembg portrait model."""

from pathlib import Path
import os

from app.config import get_settings


def main() -> int:
    settings = get_settings()
    model_root = (settings.data_root / "models").resolve()
    model_root.mkdir(parents=True, exist_ok=True)
    os.environ["U2NET_HOME"] = str(model_root)
    from rembg import new_session

    new_session(settings.player_photo_model)
    print(f"StatX player portrait model prepared in {Path(model_root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
