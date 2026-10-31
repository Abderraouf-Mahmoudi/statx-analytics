"""Process-wide test isolation established before application imports."""

import os
from pathlib import Path
from uuid import uuid4


TEST_DATABASE_PATH = (
    Path(__file__).resolve().parents[1]
    / ".pytest_cache"
    / "databases"
    / f"statx_suite_{uuid4().hex}.db"
)
TEST_DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DATABASE_PATH.as_posix()}"
os.environ["STATX_TEST_DATABASE_PATH"] = str(TEST_DATABASE_PATH)

