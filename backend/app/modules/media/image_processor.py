"""Decode, sanitize, normalize, and segment untrusted player portraits."""

from dataclasses import dataclass
from functools import lru_cache
from io import BytesIO
from typing import BinaryIO, Callable

from PIL import Image, ImageOps, UnidentifiedImageError


class InvalidPlayerImage(ValueError):
    """Image bytes violate the accepted portrait contract."""


class MediaProcessingError(RuntimeError):
    """A validated image could not be segmented."""


@dataclass(frozen=True)
class NormalizedImage:
    content: bytes
    mime_type: str
    width: int
    height: int


@dataclass(frozen=True)
class ProcessedPortrait:
    content: bytes
    width: int = 800
    height: int = 1000
    mime_type: str = "image/png"


@lru_cache(maxsize=4)
def _rembg_session(model_name: str):
    from rembg import new_session

    return new_session(model_name)


def _default_remover(model_name: str) -> Callable[[bytes], bytes]:
    def remove_background(content: bytes) -> bytes:
        from rembg import remove

        return remove(content, session=_rembg_session(model_name))

    return remove_background


class ImageProcessor:
    allowed_formats = {"JPEG", "PNG", "WEBP"}

    def __init__(
        self,
        *,
        max_bytes: int,
        max_pixels: int,
        model_name: str = "u2net_human_seg",
        remover: Callable[[bytes], bytes] | None = None,
    ) -> None:
        self.max_bytes = max_bytes
        self.max_pixels = max_pixels
        self.remover = remover or _default_remover(model_name)

    def validate_and_normalize(self, source: BinaryIO) -> NormalizedImage:
        content = source.read(self.max_bytes + 1)
        if not content or len(content) > self.max_bytes:
            raise InvalidPlayerImage("Player photo is empty or exceeds the 10 MiB limit")
        try:
            with Image.open(BytesIO(content)) as opened:
                if opened.format not in self.allowed_formats:
                    raise InvalidPlayerImage("Only JPEG, PNG, and WebP photos are accepted")
                width, height = opened.size
                if width <= 0 or height <= 0 or width * height > self.max_pixels:
                    raise InvalidPlayerImage("Decoded player photo dimensions are unsafe")
                opened.load()
                oriented = ImageOps.exif_transpose(opened)
                normalized = oriented.convert("RGB")
                output = BytesIO()
                normalized.save(output, format="PNG", optimize=True)
        except InvalidPlayerImage:
            raise
        except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as exc:
            raise InvalidPlayerImage("Player photo bytes are not a valid image") from exc
        return NormalizedImage(
            content=output.getvalue(),
            mime_type="image/png",
            width=normalized.width,
            height=normalized.height,
        )

    def remove_background(self, image: NormalizedImage) -> ProcessedPortrait:
        try:
            removed = self.remover(image.content)
            with Image.open(BytesIO(removed)) as opened:
                subject = opened.convert("RGBA")
                alpha = subject.getchannel("A")
                bounds = alpha.getbbox()
                if bounds is None:
                    raise MediaProcessingError("Segmentation produced an empty portrait")
                subject = subject.crop(bounds)
                subject.thumbnail((720, 940), Image.Resampling.LANCZOS)
                canvas = Image.new("RGBA", (800, 1000), (0, 0, 0, 0))
                x = (canvas.width - subject.width) // 2
                y = canvas.height - subject.height
                canvas.alpha_composite(subject, (x, y))
                output = BytesIO()
                canvas.save(output, format="PNG", optimize=True)
                return ProcessedPortrait(output.getvalue())
        except MediaProcessingError:
            raise
        except Exception as exc:
            raise MediaProcessingError("Player portrait background removal failed") from exc
