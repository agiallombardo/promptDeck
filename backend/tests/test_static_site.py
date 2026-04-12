"""Regression tests for optional STATIC_SITE_DIR SPA fallback."""

from __future__ import annotations

from pathlib import Path

from app.main import _install_static_site
from fastapi import FastAPI
from fastapi.testclient import TestClient


def test_static_spa_returns_404_for_api_prefix_paths(tmp_path: Path) -> None:
    (tmp_path / "index.html").write_text("<!doctype html><html></html>", encoding="utf-8")
    app = FastAPI()
    _install_static_site(app, tmp_path)
    client = TestClient(app)
    assert client.get("/api").status_code == 404
    assert client.get("/api/wrong").status_code == 404
    assert client.get("/").status_code == 200
