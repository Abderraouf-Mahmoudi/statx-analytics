"""Persisted player-photo download and processing worker."""

import asyncio

from sqlalchemy import exists, select
from sqlalchemy.orm import sessionmaker

from app.config import Settings
from app.db.database import SessionLocal
from app.modules.media.models import PlayerPhoto
from app.modules.media.service import PlayerMediaService, default_processor
from app.modules.roster.models import Player


def run_pending_photos_once(
    settings: Settings,
    *,
    session_factory: sessionmaker = SessionLocal,
) -> int:
    with session_factory() as session:
        service = PlayerMediaService(session, settings, default_processor(settings))
        provider_player = session.scalar(
            select(Player)
            .where(
                Player.provider == "api_football",
                Player.provider_photo_url.is_not(None),
                ~exists().where(PlayerPhoto.player_id == Player.id),
            )
            .order_by(Player.id)
        )
        if provider_player is not None:
            try:
                service.queue_provider_portrait(
                    provider_player.organization_id,
                    provider_player.public_id,
                    provider_player.provider_photo_url,
                )
                session.commit()
            except Exception:
                session.rollback()
        processed = service.process_pending_once()
        session.commit()
        return processed


async def media_worker_loop(stop: asyncio.Event, settings: Settings) -> None:
    while not stop.is_set():
        await asyncio.to_thread(run_pending_photos_once, settings)
        try:
            await asyncio.wait_for(stop.wait(), timeout=settings.provider_worker_poll_seconds)
        except TimeoutError:
            pass
