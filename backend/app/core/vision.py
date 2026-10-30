"""YOLO detection, ByteTrack tracking, and pitch homography projection."""

from collections.abc import Callable, Sequence
from datetime import datetime, timezone
from functools import lru_cache
import json
import logging
import os
from pathlib import Path
from threading import Lock
from typing import Any
from uuid import uuid4

from app.core.video_processor import PROJECT_ROOT, validate_identifier


FIELD_LENGTH_METERS = 105.0
FIELD_WIDTH_METERS = 68.0
TRACKING_EXPORT_DIR = PROJECT_ROOT / "data" / "exports" / "tracking"
PLAYER_LABELS = {"person", "player", "goalkeeper"}
BALL_LABELS = {"sports ball", "ball", "football"}
VISION_JOB_LOCK = Lock()
logger = logging.getLogger(__name__)


class VisionProcessingError(RuntimeError):
    """Raised when a clip cannot be decoded, detected, or projected."""


def _load_dependencies() -> tuple[Any, Any, Any]:
    try:
        import cv2
        import numpy as np
        import supervision as sv
    except ImportError as exc:
        raise VisionProcessingError(
            "Computer vision dependencies are missing; install the backend requirements"
        ) from exc
    return cv2, np, sv


@lru_cache(maxsize=2)
def _load_model(model_path: str) -> Any:
    try:
        from ultralytics import YOLO

        return YOLO(model_path)
    except Exception as exc:
        raise VisionProcessingError(f"Unable to load YOLO model '{model_path}'") from exc


def _model_names(model: Any) -> dict[int, str]:
    names = model.names
    if isinstance(names, dict):
        return {int(class_id): str(label) for class_id, label in names.items()}
    return {index: str(label) for index, label in enumerate(names)}


def _detection_classes(model: Any) -> tuple[set[int], set[int]]:
    names = _model_names(model)
    player_ids = {
        class_id for class_id, label in names.items() if label.lower() in PLAYER_LABELS
    }
    ball_ids = {
        class_id for class_id, label in names.items() if label.lower() in BALL_LABELS
    }
    if not player_ids:
        raise VisionProcessingError("The selected YOLO model has no player/person class")
    return player_ids, ball_ids


def build_homography(
    frame_width: int,
    frame_height: int,
    source_points: Sequence[Sequence[float]] | None = None,
) -> tuple[Any, str]:
    """Build a pixel-to-pitch matrix from four ordered corner correspondences.

    Source order is bottom-left, bottom-right, top-right, top-left. When no
    camera calibration is supplied, the full video frame is mapped to the
    standard 105 x 68 metre pitch rectangle.
    """
    cv2, np, _ = _load_dependencies()
    if frame_width <= 1 or frame_height <= 1:
        raise VisionProcessingError("Video frame dimensions are invalid")

    calibration = "custom" if source_points is not None else "frame_corners"
    points = source_points or (
        (0.0, float(frame_height - 1)),
        (float(frame_width - 1), float(frame_height - 1)),
        (float(frame_width - 1), 0.0),
        (0.0, 0.0),
    )
    source = np.asarray(points, dtype=np.float32)
    if source.shape != (4, 2):
        raise ValueError("source_points must contain four [u, v] coordinates")
    destination = np.asarray(
        (
            (0.0, 0.0),
            (FIELD_LENGTH_METERS, 0.0),
            (FIELD_LENGTH_METERS, FIELD_WIDTH_METERS),
            (0.0, FIELD_WIDTH_METERS),
        ),
        dtype=np.float32,
    )
    matrix, _ = cv2.findHomography(source, destination, method=0)
    if matrix is None:
        raise VisionProcessingError("Homography calibration could not be computed")
    return matrix, calibration


def project_points(points: Sequence[Sequence[float]], matrix: Any) -> list[tuple[float, float]]:
    """Project pixel points into bounded metric pitch coordinates."""
    cv2, np, _ = _load_dependencies()
    if not points:
        return []
    pixel_points = np.asarray(points, dtype=np.float32).reshape(-1, 1, 2)
    projected = cv2.perspectiveTransform(pixel_points, matrix).reshape(-1, 2)
    projected[:, 0] = np.clip(projected[:, 0], 0.0, FIELD_LENGTH_METERS)
    projected[:, 1] = np.clip(projected[:, 1], 0.0, FIELD_WIDTH_METERS)
    return [(round(float(x), 3), round(float(y), 3)) for x, y in projected]


def track_clip(
    video_path: str | Path,
    source_points: Sequence[Sequence[float]] | None = None,
    confidence: float = 0.25,
    frame_stride: int = 1,
    model_path: str | None = None,
    progress_callback: Callable[[int, int], None] | None = None,
) -> dict[str, Any]:
    """Detect players/ball, assign ByteTrack IDs, and return 2D trajectories."""
    cv2, np, sv = _load_dependencies()
    path = Path(video_path).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError("Clip not found")
    if not 0 < confidence <= 1:
        raise ValueError("confidence must be between 0 and 1")
    if frame_stride < 1:
        raise ValueError("frame_stride must be at least 1")

    selected_model = model_path or os.getenv("VISION_MODEL_PATH", "yolov8n.pt")
    model = _load_model(selected_model)
    player_classes, ball_classes = _detection_classes(model)
    tracked_classes = sorted(player_classes | ball_classes)

    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise VisionProcessingError("OpenCV could not open the clip")

    fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
    if fps <= 0:
        fps = 25.0
    total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    homography, calibration = build_homography(width, height, source_points)
    tracker = sv.ByteTrack(frame_rate=max(1, round(fps)))

    trajectories: list[dict[str, Any]] = []
    ball_trajectory: list[dict[str, Any]] = []
    frame_index = 0
    processed_frames = 0
    try:
        while True:
            success, frame = capture.read()
            if not success:
                break
            if frame_index % frame_stride != 0:
                frame_index += 1
                continue

            result = model.predict(
                frame,
                conf=confidence,
                classes=tracked_classes,
                verbose=False,
            )[0]
            detections = sv.Detections.from_ultralytics(result)
            if len(detections) > 0 and detections.class_id is not None:
                mask = np.isin(detections.class_id, tracked_classes)
                detections = detections[mask]
            tracked = tracker.update_with_detections(detections)

            if (
                len(tracked) > 0
                and tracked.tracker_id is not None
                and tracked.class_id is not None
                and tracked.confidence is not None
            ):
                foot_points = [
                    ((float(box[0]) + float(box[2])) / 2.0, float(box[3]))
                    for box in tracked.xyxy
                ]
                pitch_points = project_points(foot_points, homography)
                timestamp = round(frame_index / fps, 3)
                for class_id, tracker_id, score, (x, y) in zip(
                    tracked.class_id,
                    tracked.tracker_id,
                    tracked.confidence,
                    pitch_points,
                ):
                    entry = {
                        "frame": frame_index,
                        "timestamp": timestamp,
                        "x": x,
                        "y": y,
                        "confidence": round(float(score), 4),
                    }
                    if int(class_id) in player_classes:
                        trajectories.append({"player_id": int(tracker_id), **entry})
                    elif int(class_id) in ball_classes:
                        ball_trajectory.append({"ball_id": int(tracker_id), **entry})

            processed_frames += 1
            if progress_callback and (
                processed_frames == 1 or processed_frames % 25 == 0
            ):
                progress_callback(frame_index + 1, total_frames)
            frame_index += 1
    finally:
        capture.release()

    if progress_callback:
        progress_callback(total_frames or frame_index, total_frames or frame_index)
    return {
        "video": {
            "filename": path.name,
            "fps": round(fps, 3),
            "total_frames": total_frames or frame_index,
            "processed_frames": processed_frames,
            "frame_stride": frame_stride,
        },
        "field": {
            "length": FIELD_LENGTH_METERS,
            "width": FIELD_WIDTH_METERS,
            "unit": "meters",
            "calibration": calibration,
            "homography": [
                [round(float(value), 8) for value in row] for row in homography.tolist()
            ],
        },
        "model": {
            "path": selected_model,
            "tracker": "ByteTrack",
            "confidence": confidence,
        },
        "trajectories": trajectories,
        "ball_trajectory": ball_trajectory,
    }


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _job_path(job_id: str) -> Path:
    normalized = validate_identifier(job_id, "job_id")
    return TRACKING_EXPORT_DIR / f"{normalized}.json"


def _write_job(payload: dict[str, Any]) -> None:
    TRACKING_EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = _job_path(str(payload["job_id"]))
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    temporary.replace(path)


def read_tracking_job(job_id: str) -> dict[str, Any] | None:
    """Read a persisted tracking job, returning None when it does not exist."""
    try:
        path = _job_path(job_id)
    except ValueError:
        return None
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def create_tracking_job(clip_id: str, options: dict[str, Any]) -> dict[str, Any]:
    """Persist and return a queued tracking job descriptor."""
    job_id = str(uuid4())
    payload = {
        "job_id": job_id,
        "clip_id": clip_id,
        "status": "queued",
        "progress": 0.0,
        "created_at": _utc_now(),
        "updated_at": _utc_now(),
        "options": options,
        "result": None,
        "error": None,
    }
    _write_job(payload)
    return payload


def _update_job(job_id: str, **updates: Any) -> None:
    payload = read_tracking_job(job_id)
    if payload is None:
        return
    payload.update(updates)
    payload["updated_at"] = _utc_now()
    _write_job(payload)


def run_tracking_job(job_id: str, video_path: str, options: dict[str, Any]) -> None:
    """BackgroundTasks entry point that serializes heavyweight inference jobs."""
    try:
        with VISION_JOB_LOCK:
            _update_job(job_id, status="processing", progress=0.0)

            def report_progress(current: int, total: int) -> None:
                progress = round(current / total * 100, 1) if total else 0.0
                _update_job(job_id, status="processing", progress=min(progress, 99.9))

            result = track_clip(
                video_path,
                source_points=options.get("source_points"),
                confidence=float(options.get("confidence", 0.25)),
                frame_stride=int(options.get("frame_stride", 1)),
                progress_callback=report_progress,
            )
            _update_job(
                job_id,
                status="completed",
                progress=100.0,
                result=result,
                error=None,
            )
    except Exception as exc:
        logger.exception("Computer vision tracking job %s failed", job_id)
        _update_job(
            job_id,
            status="failed",
            error=str(exc),
            result=None,
        )

