"""Upload, lossless trimming, and range streaming endpoints for match videos."""

import os
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, Request, UploadFile, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from app.core.video_processor import (
    RAW_VIDEO_DIR,
    FFmpegUnavailableError,
    VideoProcessingError,
    clip_path,
    ensure_video_directories,
    iter_file_range,
    parse_range_header,
    parse_timecode,
    trim_video,
)
from app.core.vision import (
    create_tracking_job,
    read_tracking_job,
    run_tracking_job,
)


router = APIRouter(prefix="/api/video", tags=["video"])
UPLOAD_CHUNK_SIZE = 4 * 1024 * 1024
MAX_UPLOAD_BYTES = int(os.getenv("MAX_VIDEO_UPLOAD_BYTES", str(30 * 1024**3)))
ALLOWED_MP4_TYPES = {"video/mp4", "application/mp4", "application/octet-stream"}


class TrimRequest(BaseModel):
    """Validated trim request using absolute match timecodes."""

    model_config = ConfigDict(str_strip_whitespace=True)

    video_id: str
    start_time: str
    end_time: str

    @field_validator("start_time", "end_time")
    @classmethod
    def validate_timecode(cls, value: str) -> str:
        parse_timecode(value)
        return value

    @model_validator(mode="after")
    def validate_interval(self) -> "TrimRequest":
        if parse_timecode(self.end_time) <= parse_timecode(self.start_time):
            raise ValueError("end_time must be greater than start_time")
        return self


class VideoUploadResponse(BaseModel):
    video_id: str
    original_filename: str
    size_bytes: int


class TrimResponse(BaseModel):
    clip_id: str
    start_time: str
    end_time: str
    stream_url: str


class TrackRequest(BaseModel):
    """Optional inference and camera-calibration parameters."""

    source_points: list[tuple[float, float]] | None = None
    confidence: float = 0.25
    frame_stride: int = 1

    @field_validator("source_points")
    @classmethod
    def validate_source_points(
        cls,
        value: list[tuple[float, float]] | None,
    ) -> list[tuple[float, float]] | None:
        if value is not None and len(value) != 4:
            raise ValueError("source_points must contain exactly four [u, v] points")
        return value

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, value: float) -> float:
        if not 0 < value <= 1:
            raise ValueError("confidence must be between 0 and 1")
        return value

    @field_validator("frame_stride")
    @classmethod
    def validate_frame_stride(cls, value: int) -> int:
        if value < 1:
            raise ValueError("frame_stride must be at least 1")
        return value


class TrackJobResponse(BaseModel):
    job_id: str
    clip_id: str
    status: str
    progress: float
    status_url: str


@router.post(
    "/upload",
    response_model=VideoUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_video(file: UploadFile = File(...)) -> VideoUploadResponse:
    """Stream an MP4 upload to ignored raw-video storage."""
    filename = file.filename or "match.mp4"
    if Path(filename).suffix.lower() != ".mp4" or file.content_type not in ALLOWED_MP4_TYPES:
        raise HTTPException(status_code=415, detail="Only MP4 match videos are supported")

    ensure_video_directories()
    video_id = str(uuid4())
    destination = RAW_VIDEO_DIR / f"{video_id}.mp4"
    size = 0
    try:
        with destination.open("wb") as output:
            while chunk := await file.read(UPLOAD_CHUNK_SIZE):
                size += len(chunk)
                if size > MAX_UPLOAD_BYTES:
                    raise HTTPException(status_code=413, detail="Video exceeds the upload size limit")
                output.write(chunk)
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    finally:
        await file.close()

    if size == 0:
        destination.unlink(missing_ok=True)
        raise HTTPException(status_code=422, detail="Uploaded video is empty")
    return VideoUploadResponse(
        video_id=video_id,
        original_filename=filename,
        size_bytes=size,
    )


@router.post("/trim", response_model=TrimResponse)
def create_video_clip(payload: TrimRequest) -> TrimResponse:
    """Cut an MP4 excerpt with FFmpeg stream copy."""
    try:
        result = trim_video(payload.video_id, payload.start_time, payload.end_time)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except FFmpegUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except VideoProcessingError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return TrimResponse(
        clip_id=result.clip_id,
        start_time=result.start_time,
        end_time=result.end_time,
        stream_url=f"/api/video/stream/{result.clip_id}",
    )


@router.post(
    "/track/{clip_id}",
    response_model=TrackJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def start_clip_tracking(
    clip_id: str,
    background_tasks: BackgroundTasks,
    payload: TrackRequest | None = None,
) -> TrackJobResponse:
    """Queue YOLO + ByteTrack inference without blocking the API response."""
    try:
        path = clip_path(clip_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Clip not found") from exc
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Clip not found")

    request = payload or TrackRequest()
    options = request.model_dump()
    job = create_tracking_job(clip_id, options)
    background_tasks.add_task(run_tracking_job, job["job_id"], str(path), options)
    return TrackJobResponse(
        job_id=job["job_id"],
        clip_id=clip_id,
        status=job["status"],
        progress=job["progress"],
        status_url=f"/api/video/track/jobs/{job['job_id']}",
    )


@router.get("/track/jobs/{job_id}")
def get_tracking_job(job_id: str) -> dict[str, object]:
    """Return progress, failure details, or completed metric trajectories."""
    job = read_tracking_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Tracking job not found")
    return job


@router.get("/stream/{clip_id}")
def stream_video_clip(clip_id: str, request: Request) -> StreamingResponse:
    """Serve an exported clip with single-range HTTP streaming support."""
    try:
        path = clip_path(clip_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Clip not found") from exc
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Clip not found")

    file_size = path.stat().st_size
    range_header = request.headers.get("range")
    common_headers = {
        "Accept-Ranges": "bytes",
        "Content-Type": "video/mp4",
        "Content-Disposition": f'inline; filename="{path.name}"',
    }

    if range_header:
        try:
            start, end = parse_range_header(range_header, file_size)
        except ValueError as exc:
            raise HTTPException(
                status_code=416,
                detail="Requested range is not satisfiable",
                headers={"Content-Range": f"bytes */{file_size}"},
            ) from exc
        headers = {
            **common_headers,
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Content-Length": str(end - start + 1),
        }
        return StreamingResponse(
            iter_file_range(path, start, end),
            status_code=status.HTTP_206_PARTIAL_CONTENT,
            media_type="video/mp4",
            headers=headers,
        )

    return StreamingResponse(
        iter_file_range(path, 0, file_size - 1),
        media_type="video/mp4",
        headers={**common_headers, "Content-Length": str(file_size)},
    )

