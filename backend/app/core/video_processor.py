"""Safe FFmpeg orchestration and byte-range helpers for match videos."""

from dataclasses import dataclass
import os
from pathlib import Path
import re
import shutil
import subprocess
from collections.abc import Iterator
from uuid import UUID, uuid4


PROJECT_ROOT = Path(__file__).resolve().parents[3]
RAW_VIDEO_DIR = PROJECT_ROOT / "data" / "raw_videos"
CLIP_EXPORT_DIR = PROJECT_ROOT / "data" / "exports" / "clips"
TIME_CODE_PATTERN = re.compile(r"^(?P<hours>\d{2,3}):(?P<minutes>[0-5]\d):(?P<seconds>[0-5]\d)$")
RANGE_PATTERN = re.compile(r"^bytes=(?P<start>\d*)-(?P<end>\d*)$")


class VideoProcessingError(RuntimeError):
    """Raised when FFmpeg cannot produce the requested clip."""


class FFmpegUnavailableError(VideoProcessingError):
    """Raised when no FFmpeg executable is available."""


@dataclass(frozen=True)
class ClipResult:
    """Metadata returned after a successful lossless trim."""

    clip_id: str
    path: Path
    start_time: str
    end_time: str


def ensure_video_directories() -> None:
    """Create the ignored storage directories used by the video module."""
    RAW_VIDEO_DIR.mkdir(parents=True, exist_ok=True)
    CLIP_EXPORT_DIR.mkdir(parents=True, exist_ok=True)


def parse_timecode(value: str) -> int:
    """Validate an HH:MM:SS timecode and return its value in seconds."""
    match = TIME_CODE_PATTERN.fullmatch(value.strip())
    if match is None:
        raise ValueError("Timecodes must use the HH:MM:SS format")
    return (
        int(match.group("hours")) * 3600
        + int(match.group("minutes")) * 60
        + int(match.group("seconds"))
    )


def validate_identifier(value: str, label: str = "identifier") -> str:
    """Normalize UUID identifiers and reject traversal or arbitrary filenames."""
    try:
        return str(UUID(value))
    except (ValueError, AttributeError) as exc:
        raise ValueError(f"Invalid {label}") from exc


def raw_video_path(video_id: str) -> Path:
    """Resolve a video UUID to its source MP4 path."""
    return RAW_VIDEO_DIR / f"{validate_identifier(video_id, 'video_id')}.mp4"


def clip_path(clip_id: str) -> Path:
    """Resolve a clip UUID to its exported MP4 path."""
    return CLIP_EXPORT_DIR / f"{validate_identifier(clip_id, 'clip_id')}.mp4"


def trim_video(video_id: str, start_time: str, end_time: str) -> ClipResult:
    """Create an MP4 excerpt with stream copy, avoiding expensive re-encoding."""
    start_seconds = parse_timecode(start_time)
    end_seconds = parse_timecode(end_time)
    if end_seconds <= start_seconds:
        raise ValueError("end_time must be greater than start_time")

    ensure_video_directories()
    source = raw_video_path(video_id)
    if not source.is_file():
        raise FileNotFoundError("Source video not found")

    ffmpeg = resolve_ffmpeg_binary()
    if not ffmpeg:
        raise FFmpegUnavailableError(
            "FFmpeg is not installed or FFMPEG_BINARY does not point to an executable"
        )

    clip_id = str(uuid4())
    destination = CLIP_EXPORT_DIR / f"{clip_id}.mp4"
    command = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-ss",
        start_time,
        "-to",
        end_time,
        "-i",
        str(source),
        "-c",
        "copy",
        "-movflags",
        "+faststart",
        str(destination),
    ]

    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=int(os.getenv("FFMPEG_TIMEOUT_SECONDS", "1800")),
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        destination.unlink(missing_ok=True)
        raise VideoProcessingError("FFmpeg could not complete the trim operation") from exc

    if completed.returncode != 0 or not destination.is_file() or destination.stat().st_size == 0:
        destination.unlink(missing_ok=True)
        detail = completed.stderr.strip()[-800:] or "unknown FFmpeg error"
        raise VideoProcessingError(f"FFmpeg trim failed: {detail}")

    return ClipResult(
        clip_id=clip_id,
        path=destination,
        start_time=start_time,
        end_time=end_time,
    )


def resolve_ffmpeg_binary() -> str:
    """Resolve configured, system, or packaged FFmpeg in priority order."""
    configured = os.getenv("FFMPEG_BINARY")
    if configured:
        configured_path = Path(configured).expanduser()
        if configured_path.is_file():
            return str(configured_path.resolve())
        discovered = shutil.which(configured)
        if discovered:
            return discovered

    discovered = shutil.which("ffmpeg")
    if discovered:
        return discovered
    try:
        from imageio_ffmpeg import get_ffmpeg_exe

        packaged = Path(get_ffmpeg_exe())
        if packaged.is_file():
            return str(packaged)
    except (ImportError, RuntimeError, OSError):
        pass
    raise FFmpegUnavailableError(
        "FFmpeg is unavailable; install it, configure FFMPEG_BINARY, or install imageio-ffmpeg"
    )


def parse_range_header(range_header: str, file_size: int) -> tuple[int, int]:
    """Parse one RFC 7233 byte range into an inclusive start/end pair."""
    match = RANGE_PATTERN.fullmatch(range_header.strip())
    if match is None or file_size <= 0:
        raise ValueError("Invalid Range header")

    start_text = match.group("start")
    end_text = match.group("end")
    if not start_text and not end_text:
        raise ValueError("Invalid Range header")

    if not start_text:
        suffix_length = int(end_text)
        if suffix_length <= 0:
            raise ValueError("Invalid suffix range")
        start = max(file_size - suffix_length, 0)
        end = file_size - 1
    else:
        start = int(start_text)
        end = int(end_text) if end_text else file_size - 1
        if start >= file_size or end < start:
            raise ValueError("Range is outside the file")
        end = min(end, file_size - 1)

    return start, end


def iter_file_range(
    path: Path,
    start: int,
    end: int,
    chunk_size: int = 1024 * 1024,
) -> Iterator[bytes]:
    """Yield only the requested inclusive byte range without loading it in memory."""
    remaining = end - start + 1
    with path.open("rb") as stream:
        stream.seek(start)
        while remaining > 0:
            chunk = stream.read(min(chunk_size, remaining))
            if not chunk:
                break
            remaining -= len(chunk)
            yield chunk

