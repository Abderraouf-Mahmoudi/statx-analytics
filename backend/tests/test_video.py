"""Tests for timecodes, FFmpeg orchestration, and HTTP byte ranges."""

from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.core import video_processor


def test_parse_timecode_and_ranges() -> None:
    assert video_processor.parse_timecode("00:15:00") == 900
    assert video_processor.parse_timecode("101:02:03") == 363723
    assert video_processor.parse_range_header("bytes=10-19", 100) == (10, 19)
    assert video_processor.parse_range_header("bytes=90-", 100) == (90, 99)
    assert video_processor.parse_range_header("bytes=-10", 100) == (90, 99)
    with pytest.raises(ValueError):
        video_processor.parse_timecode("15:00")
    with pytest.raises(ValueError):
        video_processor.parse_range_header("bytes=100-120", 100)


def test_trim_video_uses_ffmpeg_stream_copy(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    clip_dir = tmp_path / "clips"
    raw_dir.mkdir()
    video_id = str(uuid4())
    (raw_dir / f"{video_id}.mp4").write_bytes(b"source-video")

    monkeypatch.setattr(video_processor, "RAW_VIDEO_DIR", raw_dir)
    monkeypatch.setattr(video_processor, "CLIP_EXPORT_DIR", clip_dir)
    monkeypatch.setattr(video_processor.shutil, "which", lambda _: "ffmpeg")
    captured: dict[str, list[str]] = {}

    def fake_run(command: list[str], **_: object) -> SimpleNamespace:
        captured["command"] = command
        Path(command[-1]).write_bytes(b"trimmed-video")
        return SimpleNamespace(returncode=0, stderr="")

    monkeypatch.setattr(video_processor.subprocess, "run", fake_run)
    result = video_processor.trim_video(video_id, "00:15:00", "00:30:00")

    assert result.path.read_bytes() == b"trimmed-video"
    assert captured["command"][captured["command"].index("-c") + 1] == "copy"
    assert captured["command"][captured["command"].index("-ss") + 1] == "00:15:00"
    assert captured["command"][captured["command"].index("-to") + 1] == "00:30:00"


def test_iter_file_range_returns_only_requested_bytes(tmp_path: Path) -> None:
    source = tmp_path / "clip.mp4"
    source.write_bytes(b"0123456789")
    assert b"".join(video_processor.iter_file_range(source, 2, 6, chunk_size=2)) == b"23456"

