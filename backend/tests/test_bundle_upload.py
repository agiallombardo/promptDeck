import io
import zipfile

import pytest
from app.services.bundle_upload import choose_bundle_entrypoint, extract_zip_bundle


def test_choose_entry_shallowest_index() -> None:
    assert choose_bundle_entrypoint(["dist/index.html", "index.html"]) == "index.html"


def test_choose_entry_index_htm() -> None:
    assert choose_bundle_entrypoint(["x/index.htm"]) == "x/index.htm"


def test_choose_single_html_when_no_index() -> None:
    assert choose_bundle_entrypoint(["slides/deck.html"]) == "slides/deck.html"


def test_choose_rejects_multiple_html_without_index() -> None:
    with pytest.raises(ValueError, match="index"):
        choose_bundle_entrypoint(["a.html", "b.html"])


def test_choose_rejects_empty() -> None:
    with pytest.raises(ValueError):
        choose_bundle_entrypoint([])


def test_extract_zip_writes_and_returns_entry(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("STORAGE_ROOT", str(tmp_path / "store"))
    from app.config import get_settings

    get_settings.cache_clear()
    settings = get_settings()

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(
            "index.html",
            "<!DOCTYPE html><html><body><section>One</section></body></html>",
        )
        zf.writestr("assets/app.css", "body { margin: 0; }")
    raw = buf.getvalue()

    entry = extract_zip_bundle(settings, "presentations/p1/v1", raw)
    assert entry == "index.html"

    base = tmp_path / "store" / "presentations" / "p1" / "v1"
    assert (base / "index.html").is_file()
    assert (base / "assets" / "app.css").is_file()

    get_settings.cache_clear()
