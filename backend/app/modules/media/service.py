"""Organization-scoped player portrait persistence and processing."""

from datetime import datetime, timezone
import hashlib
from io import BytesIO
import os
from pathlib import Path
from typing import BinaryIO
from urllib.parse import urlsplit
from uuid import uuid4

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.modules.identity.service import ResourceNotFound
from app.modules.media.image_processor import ImageProcessor, NormalizedImage
from app.modules.media.models import PlayerPhoto
from app.modules.organizations.models import Organization
from app.modules.platform.audit import write_audit
from app.modules.roster.models import Player


class PlayerMediaService:
    def __init__(self, session: Session, settings: Settings, processor: ImageProcessor) -> None:
        self.session = session
        self.settings = settings
        self.processor = processor
        self.data_root = settings.data_root.resolve()

    def _player(self, organization_id: int, player_public_id: str) -> Player:
        player = self.session.scalar(
            select(Player).where(
                Player.organization_id == organization_id,
                Player.public_id == player_public_id,
            )
        )
        if player is None:
            raise ResourceNotFound("Resource not found")
        return player

    def _relative_directory(self, organization_id: int, player: Player) -> Path:
        organization = self.session.get(Organization, organization_id)
        if organization is None:
            raise ResourceNotFound("Resource not found")
        return Path("player_photos") / organization.public_id / player.public_id

    def _write_atomic(self, relative_path: Path, content: bytes) -> None:
        destination = (self.data_root / relative_path).resolve()
        if self.data_root not in destination.parents:
            raise ValueError("Unsafe media destination")
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_name(f".{destination.name}.{uuid4().hex}.tmp")
        with temporary.open("wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)

    def queue_upload(
        self,
        organization_id: int,
        player_public_id: str,
        source: str,
        stream: BinaryIO,
    ) -> PlayerPhoto:
        if source not in {"camera", "gallery"}:
            raise ValueError("Photo source must be camera or gallery")
        normalized = self.processor.validate_and_normalize(stream)
        return self._queue_normalized(
            organization_id,
            player_public_id,
            source,
            normalized,
            rights_status="club_authorized",
        )

    def _queue_normalized(
        self,
        organization_id: int,
        player_public_id: str,
        source: str,
        normalized: NormalizedImage,
        *,
        rights_status: str,
    ) -> PlayerPhoto:
        player = self._player(organization_id, player_public_id)
        digest = hashlib.sha256(normalized.content).hexdigest()
        directory = self._relative_directory(organization_id, player)
        original = directory / f"{digest}-original.png"
        self._write_atomic(original, normalized.content)
        photo = PlayerPhoto(
            player_id=player.id,
            source=source,
            original_path=original.as_posix(),
            mime_type=normalized.mime_type,
            sha256=digest,
            width=normalized.width,
            height=normalized.height,
            processing_status="pending",
            rights_status=rights_status,
        )
        self.session.add(photo)
        self.session.flush()
        write_audit(
            self.session,
            actor_id=None,
            organization_id=organization_id,
            action="player.photo_uploaded",
            entity_type="player_photo",
            entity_public_id=photo.public_id,
            after={"source": source, "sha256": digest},
        )
        return photo

    def queue_provider_portrait(
        self,
        organization_id: int,
        player_public_id: str,
        url: str,
        *,
        http_client: httpx.Client | None = None,
    ) -> PlayerPhoto:
        parsed = urlsplit(url)
        allowed_hosts = {host.lower() for host in self.settings.api_football_media_hosts}
        if parsed.scheme != "https" or (parsed.hostname or "").lower() not in allowed_hosts:
            raise ValueError("Provider portrait host is not approved")
        owns_client = http_client is None
        client = http_client or httpx.Client(follow_redirects=False, timeout=20)
        try:
            with client.stream("GET", url) as response:
                if response.status_code != 200:
                    raise ValueError("Provider portrait download failed")
                collected = bytearray()
                for chunk in response.iter_bytes():
                    collected.extend(chunk)
                    if len(collected) > self.settings.max_player_photo_bytes:
                        raise ValueError("Provider portrait exceeds the upload limit")
            normalized = self.processor.validate_and_normalize(BytesIO(bytes(collected)))
            return self._queue_normalized(
                organization_id,
                player_public_id,
                "api_football",
                normalized,
                rights_status="provider_identification_only",
            )
        finally:
            if owns_client:
                client.close()

    def process_pending_once(self) -> int:
        photo = self.session.scalar(
            select(PlayerPhoto)
            .where(PlayerPhoto.processing_status == "pending")
            .order_by(PlayerPhoto.created_at)
        )
        if photo is None:
            return 0
        photo.processing_status = "processing"
        self.session.flush()
        try:
            original_path = (self.data_root / str(photo.original_path)).resolve()
            content = original_path.read_bytes()
            normalized = NormalizedImage(
                content=content,
                mime_type=photo.mime_type or "image/png",
                width=photo.width or 0,
                height=photo.height or 0,
            )
            portrait = self.processor.remove_background(normalized)
            relative = Path(str(photo.original_path)).with_name(
                f"{photo.sha256}-cutout.png"
            )
            self._write_atomic(relative, portrait.content)
            photo.cutout_path = relative.as_posix()
            photo.width = portrait.width
            photo.height = portrait.height
            photo.processing_status = "ready"
            photo.error_summary = None
            photo.processed_at = datetime.now(timezone.utc)
            self.session.flush()
            return 1
        except Exception as exc:
            photo.processing_status = "failed"
            photo.error_summary = type(exc).__name__
            photo.processed_at = datetime.now(timezone.utc)
            self.session.flush()
            return 0

    def current_photo(self, organization_id: int, player_public_id: str) -> PlayerPhoto:
        player = self._player(organization_id, player_public_id)
        photo = self.session.scalar(
            select(PlayerPhoto)
            .where(PlayerPhoto.player_id == player.id)
            .order_by(
                (PlayerPhoto.source.in_(["camera", "gallery"])).desc(),
                PlayerPhoto.created_at.desc(),
            )
        )
        if photo is None:
            raise ResourceNotFound("Resource not found")
        return photo

    def delete_current(self, organization_id: int, player_public_id: str) -> PlayerPhoto:
        photo = self.current_photo(organization_id, player_public_id)
        self.session.delete(photo)
        self.session.flush()
        write_audit(
            self.session,
            actor_id=None,
            organization_id=organization_id,
            action="player.photo_deleted",
            entity_type="player_photo",
            entity_public_id=photo.public_id,
            before={"sha256": photo.sha256, "source": photo.source},
        )
        return photo


def default_processor(settings: Settings) -> ImageProcessor:
    return ImageProcessor(
        max_bytes=settings.max_player_photo_bytes,
        max_pixels=settings.max_player_photo_pixels,
        model_name=settings.player_photo_model,
    )
