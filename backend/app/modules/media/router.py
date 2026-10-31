"""Authenticated player portrait upload, status, delivery, and deletion."""

from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, Request, Response, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.problems import ProblemException
from app.config import Settings, get_settings
from app.db.database import get_db
from app.modules.identity.dependencies import require_roles
from app.modules.identity.service import Actor
from app.modules.media.image_processor import InvalidPlayerImage
from app.modules.media.models import PlayerPhoto
from app.modules.media.service import PlayerMediaService, default_processor


router = APIRouter(tags=["player-media"])
editor = require_roles("admin", "analyst")
reader = require_roles("admin", "analyst", "coach", "viewer")


def _service(db: Session, settings: Settings) -> PlayerMediaService:
    return PlayerMediaService(db, settings, default_processor(settings))


def _view(photo: PlayerPhoto) -> dict:
    return {
        "public_id": photo.public_id,
        "source": photo.source,
        "status": photo.processing_status,
        "rights_status": photo.rights_status,
        "width": photo.width,
        "height": photo.height,
        "error": photo.error_summary,
    }


@router.post("/players/{player_id}/photo", status_code=status.HTTP_202_ACCEPTED)
def upload_player_photo(
    player_id: str,
    source: str = Form(...),
    photo: UploadFile = File(...),
    db: Session = Depends(get_db),
    actor: Actor = Depends(editor),
    settings: Settings = Depends(get_settings),
) -> dict:
    try:
        record = _service(db, settings).queue_upload(
            actor.organization_id, player_id, source, photo.file
        )
        db.commit()
        db.refresh(record)
        return _view(record)
    except (InvalidPlayerImage, ValueError) as exc:
        db.rollback()
        raise ProblemException(422, "invalid_player_photo", str(exc)) from exc


@router.get("/players/{player_id}/photo")
def get_player_photo(
    player_id: str,
    request: Request,
    db: Session = Depends(get_db),
    actor: Actor = Depends(reader),
    settings: Settings = Depends(get_settings),
):
    photo = _service(db, settings).current_photo(actor.organization_id, player_id)
    if photo.processing_status != "ready" or not photo.cutout_path:
        return Response(
            content=__import__("json").dumps(_view(photo)),
            status_code=status.HTTP_202_ACCEPTED,
            media_type="application/json",
        )
    etag = f'"{photo.sha256}"'
    if request.headers.get("if-none-match") == etag:
        return Response(status_code=status.HTTP_304_NOT_MODIFIED, headers={"ETag": etag})
    path = (settings.data_root.resolve() / Path(photo.cutout_path)).resolve()
    if settings.data_root.resolve() not in path.parents or not path.is_file():
        raise ProblemException(404, "photo_file_missing", "Processed player photo is unavailable")
    return FileResponse(path, media_type="image/png", headers={"ETag": etag})


@router.delete("/players/{player_id}/photo", status_code=status.HTTP_204_NO_CONTENT)
def delete_player_photo(
    player_id: str,
    db: Session = Depends(get_db),
    actor: Actor = Depends(editor),
    settings: Settings = Depends(get_settings),
) -> Response:
    _service(db, settings).delete_current(actor.organization_id, player_id)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
