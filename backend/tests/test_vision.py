"""Unit tests for homography and persistent background tracking jobs."""

from pathlib import Path

import pytest
from fastapi import BackgroundTasks

from app.api import video_routes
from app.core import vision
from app.core import video_processor


def test_frame_corner_homography_maps_to_standard_pitch() -> None:
    matrix, calibration = vision.build_homography(1920, 1080)
    projected = vision.project_points(
        [(0, 1079), (1919, 1079), (1919, 0), (0, 0)],
        matrix,
    )
    assert calibration == "frame_corners"
    assert projected == [(0.0, 0.0), (105.0, 0.0), (105.0, 68.0), (0.0, 68.0)]


def test_background_job_persists_completed_result(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(vision, "TRACKING_EXPORT_DIR", tmp_path / "jobs")
    expected = {
        "trajectories": [
            {"player_id": 7, "frame": 1, "timestamp": 0.04, "x": 52.5, "y": 34.0}
        ],
        "ball_trajectory": [],
    }

    def fake_track(*_: object, progress_callback=None, **__: object) -> dict[str, object]:
        if progress_callback:
            progress_callback(1, 2)
            progress_callback(2, 2)
        return expected

    monkeypatch.setattr(vision, "track_clip", fake_track)
    job = vision.create_tracking_job("clip-id", {"confidence": 0.25, "frame_stride": 1})
    vision.run_tracking_job(job["job_id"], "clip.mp4", job["options"])

    completed = vision.read_tracking_job(job["job_id"])
    assert completed is not None
    assert completed["status"] == "completed"
    assert completed["progress"] == 100.0
    assert completed["result"] == expected


def test_tracking_endpoint_queues_job_and_exposes_status(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    clips = tmp_path / "clips"
    clips.mkdir()
    clip_id = "e440e1d1-1ec2-4f3d-948d-aeb8b3e12665"
    (clips / f"{clip_id}.mp4").write_bytes(b"test clip")
    monkeypatch.setattr(video_processor, "CLIP_EXPORT_DIR", clips)
    monkeypatch.setattr(vision, "TRACKING_EXPORT_DIR", tmp_path / "tracking")
    tasks = BackgroundTasks()
    response = video_routes.start_clip_tracking(
        clip_id,
        tasks,
        video_routes.TrackRequest(confidence=0.4, frame_stride=3),
    )
    assert response.status == "queued"
    assert response.status_url.endswith(response.job_id)
    assert len(tasks.tasks) == 1

    persisted = video_routes.get_tracking_job(response.job_id)
    assert persisted["options"] == {
        "source_points": None,
        "confidence": 0.4,
        "frame_stride": 3,
    }

