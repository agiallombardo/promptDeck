"""Verify the full Alembic chain applies on a file-backed SQLite database."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]


def test_alembic_upgrade_head_sqlite_file() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "promptdeck.sqlite"
        url = f"sqlite+aiosqlite:///{db_path}"
        env = os.environ.copy()
        env["DATABASE_URL"] = url
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=BACKEND_ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
        assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"
        assert db_path.is_file()
