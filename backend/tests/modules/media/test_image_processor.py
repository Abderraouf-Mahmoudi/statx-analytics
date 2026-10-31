"""Untrusted player portrait normalization and cutout tests."""

from io import BytesIO

from PIL import Image
import pytest

from app.modules.media.image_processor import ImageProcessor, InvalidPlayerImage


def image_bytes(format: str = "JPEG", *, size=(320, 480), exif=None) -> bytes:
    output = BytesIO()
    options = {"exif": exif} if exif is not None else {}
    Image.new("RGB", size, "#7c3aed").save(output, format=format, **options)
    return output.getvalue()


def test_normalize_decodes_content_strips_metadata_and_honors_exif_orientation() -> None:
    exif = Image.Exif()
    exif[274] = 6
    exif[34853] = {1: "N"}
    processor = ImageProcessor(max_bytes=10 * 1024 * 1024, max_pixels=24_000_000)

    normalized = processor.validate_and_normalize(BytesIO(image_bytes(exif=exif)))

    assert (normalized.width, normalized.height) == (480, 320)
    with Image.open(BytesIO(normalized.content)) as decoded:
        assert decoded.format == "PNG"
        assert decoded.getexif() == {}


def test_normalize_rejects_bad_bytes_size_limit_and_decoded_pixel_limit() -> None:
    with pytest.raises(InvalidPlayerImage):
        ImageProcessor(max_bytes=1024, max_pixels=10_000).validate_and_normalize(BytesIO(b"not an image"))
    with pytest.raises(InvalidPlayerImage):
        ImageProcessor(max_bytes=10, max_pixels=10_000).validate_and_normalize(BytesIO(image_bytes()))
    with pytest.raises(InvalidPlayerImage):
        ImageProcessor(max_bytes=10_000, max_pixels=100).validate_and_normalize(BytesIO(image_bytes(size=(20, 20))))


def test_background_removal_outputs_fixed_transparent_portrait_canvas() -> None:
    def fake_remove(content: bytes) -> bytes:
        source = Image.open(BytesIO(content)).convert("RGBA")
        source.putalpha(180)
        output = BytesIO()
        source.save(output, format="PNG")
        return output.getvalue()

    processor = ImageProcessor(max_bytes=1_000_000, max_pixels=1_000_000, remover=fake_remove)
    normalized = processor.validate_and_normalize(BytesIO(image_bytes(size=(200, 300))))
    cutout = processor.remove_background(normalized)

    with Image.open(BytesIO(cutout.content)) as image:
        assert image.mode == "RGBA"
        assert image.size == (800, 1000)
        assert image.getextrema()[3][0] == 0

