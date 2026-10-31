"""Organization-scoped player photo workflow tests."""

from io import BytesIO

from PIL import Image
import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.config import Settings
from app.db.model_registry import Base
from app.modules.identity.service import ResourceNotFound
from app.modules.media.image_processor import ImageProcessor
from app.modules.media.service import PlayerMediaService
from app.modules.organizations.models import Organization
from app.modules.roster.models import Player


def png_bytes() -> bytes:
    output = BytesIO()
    Image.new("RGB", (160, 240), "#10b981").save(output, format="PNG")
    return output.getvalue()


def setup(tmp_path):
    engine = create_engine(f"sqlite:///{(tmp_path / 'media.db').as_posix()}")
    Base.metadata.create_all(engine)
    session = Session(engine)
    first = Organization(name="First")
    second = Organization(name="Second")
    session.add_all([first, second])
    session.flush()
    player = Player(organization_id=first.id, name="Amina", first_name="Amina", last_name="Ben", position="CM")
    session.add(player)
    session.commit()
    settings = Settings(
        database_url="sqlite://",
        data_root=tmp_path / "data",
        session_secret="test-session-secret-with-enough-entropy",
        _env_file=None,
    )
    processor = ImageProcessor(max_bytes=settings.max_player_photo_bytes, max_pixels=settings.max_player_photo_pixels, remover=lambda content: content)
    return session, first, second, player, PlayerMediaService(session, settings, processor)


def test_uploaded_photo_is_persisted_processed_and_scoped(tmp_path) -> None:
    session, first, second, player, service = setup(tmp_path)
    try:
        photo = service.queue_upload(first.id, player.public_id, "gallery", BytesIO(png_bytes()))
        session.commit()
        assert photo.processing_status == "pending"
        assert not photo.original_path.startswith(("/", "\\"))

        assert service.process_pending_once() == 1
        session.commit()
        assert photo.processing_status == "ready"
        assert (service.data_root / photo.cutout_path).is_file()
        assert service.current_photo(first.id, player.public_id).public_id == photo.public_id
        try:
            service.current_photo(second.id, player.public_id)
        except ResourceNotFound:
            pass
        else:
            raise AssertionError("Cross-organization photo access was not hidden")
    finally:
        session.close()


def test_failed_segmentation_keeps_validated_original_recoverable(tmp_path) -> None:
    session, organization, _, player, _ = setup(tmp_path)
    processor = ImageProcessor(max_bytes=1_000_000, max_pixels=1_000_000, remover=lambda _: (_ for _ in ()).throw(RuntimeError("model failure")))
    service = PlayerMediaService(session, Settings(database_url="sqlite://", data_root=tmp_path / "data", session_secret="test-session-secret-with-enough-entropy", _env_file=None), processor)
    try:
        photo = service.queue_upload(organization.id, player.public_id, "camera", BytesIO(png_bytes()))
        session.commit()
        assert service.process_pending_once() == 0
        session.commit()
        assert photo.processing_status == "failed"
        assert (service.data_root / photo.original_path).is_file()
        assert photo.cutout_path is None
    finally:
        session.close()


def test_provider_portrait_download_is_https_host_allowlisted_and_identification_only(tmp_path) -> None:
    session, organization, _, player, service = setup(tmp_path)
    try:
        with pytest.raises(ValueError):
            service.queue_provider_portrait(
                organization.id,
                player.public_id,
                "https://example.com/player.png",
                http_client=httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(200, content=png_bytes()))),
            )

        client = httpx.Client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(
                    200, content=png_bytes(), headers={"content-type": "image/png"}, request=request
                )
            ),
            follow_redirects=False,
        )
        photo = service.queue_provider_portrait(
            organization.id,
            player.public_id,
            "https://media.api-sports.io/football/players/501.png",
            http_client=client,
        )
        assert photo.source == "api_football"
        assert photo.rights_status == "provider_identification_only"
    finally:
        session.close()
