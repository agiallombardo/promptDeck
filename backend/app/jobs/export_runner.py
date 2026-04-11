from __future__ import annotations

import asyncio
import io
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright
from pypdf import PdfReader, PdfWriter
from sqlalchemy import select

from app.config import Settings, get_settings
from app.db.models.export_job import ExportFormat, ExportJob, ExportStatus
from app.db.models.presentation import PresentationVersion, Slide
from app.db.session import session_factory
from app.services.html_bundle import inline_zip_entry_to_single_html
from app.services.html_probe_inject import inject_probe_into_html
from app.storage.local import safe_join, version_dir


def _pdf_export_sync(
    job_id: uuid.UUID,
    storage_prefix: str,
    entry_rel: str,
    slide_count: int,
    options: dict[str, Any],
    out_path: Path,
) -> str | None:
    """Render deck to PDF. Returns error message or None on success."""
    settings = get_settings()
    base = version_dir(settings, storage_prefix)
    try:
        entry_file = safe_join(base, entry_rel)
    except ValueError:
        return "Invalid entry path"
    if not entry_file.is_file():
        return "Entry HTML not found"
    raw = entry_file.read_bytes()
    injected = inject_probe_into_html(raw)
    preview = entry_file.parent / f".export_job_{job_id}.html"
    try:
        preview.write_bytes(injected)
        uri = preview.resolve().as_uri()
    except OSError as e:
        return str(e)[:500]

    print_bg = bool(options.get("print_background", True))
    landscape = bool(options.get("landscape", True))
    width = str(options.get("page_width_css", "1280px"))
    height = str(options.get("page_height_css", "720px"))
    settle_ms = int(options.get("slide_settle_ms", 400))

    pdfs: list[bytes] = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                page = browser.new_page()
                page.goto(uri, wait_until="load", timeout=120_000)
                n = max(1, slide_count)
                for slide_i in range(n):
                    page.evaluate(
                        """(idx) => { window.postMessage({ type: 'goto', slide: idx }, '*'); }""",
                        slide_i,
                    )
                    page.wait_for_timeout(settle_ms)
                    pdfs.append(
                        page.pdf(
                            print_background=print_bg,
                            landscape=landscape,
                            width=width,
                            height=height,
                            margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
                        )
                    )
            finally:
                browser.close()
    except Exception as e:  # noqa: BLE001
        return f"PDF render failed: {e}"[:2000]
    finally:
        preview.unlink(missing_ok=True)

    try:
        writer = PdfWriter()
        for blob in pdfs:
            reader = PdfReader(io.BytesIO(blob))
            for pg in reader.pages:
                writer.add_page(pg)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("wb") as f:
            writer.write(f)
    except Exception as e:  # noqa: BLE001
        return f"PDF merge failed: {e}"[:2000]
    return None


def _single_html_export_sync(
    settings: Settings,
    storage_prefix: str,
    entry_rel: str,
    out_path: Path,
) -> str | None:
    """Bundle entry HTML with inlined local CSS/JS, inject slide probe; returns error or None."""
    try:
        _out_name, html_bytes = inline_zip_entry_to_single_html(settings, storage_prefix, entry_rel)
        del _out_name
    except ValueError as e:
        return str(e)[:2000]
    injected = inject_probe_into_html(html_bytes)
    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(injected)
    except OSError as e:
        return str(e)[:500]
    return None


async def run_export_job(job_id: uuid.UUID) -> None:
    fac = session_factory()
    settings = get_settings()
    err_msg: str | None = None
    storage_prefix = ""
    entry_rel = ""
    slide_count = 1
    opts: dict[str, Any] = {}
    export_format: ExportFormat | None = None

    async with fac() as session:
        job = await session.get(ExportJob, job_id)
        if job is None:
            return
        job.status = ExportStatus.running
        job.started_at = datetime.now(UTC)
        job.progress = 10
        export_format = job.format
        if job.format not in (ExportFormat.pdf, ExportFormat.single_html):
            err_msg = f"Export format {job.format!s} is not supported yet"
        else:
            ver = await session.get(PresentationVersion, job.version_id)
            if ver is None:
                err_msg = "Version not found"
            else:
                storage_prefix = ver.storage_prefix
                entry_rel = ver.entry_path
                opts = dict(job.options) if job.options else {}
                r = await session.execute(
                    select(Slide).where(Slide.version_id == ver.id).order_by(Slide.slide_index)
                )
                slides = r.scalars().all()
                slide_count = len(slides) if slides else 1
        await session.commit()

    suffix = ".pdf" if export_format == ExportFormat.pdf else ".html"
    out_path = settings.storage_root / "exports" / f"{job_id}{suffix}"

    try:
        if err_msg is None:
            if export_format == ExportFormat.pdf:
                err_msg = await asyncio.to_thread(
                    _pdf_export_sync,
                    job_id,
                    storage_prefix,
                    entry_rel,
                    slide_count,
                    opts,
                    out_path,
                )
            elif export_format == ExportFormat.single_html:
                err_msg = await asyncio.to_thread(
                    _single_html_export_sync,
                    settings,
                    storage_prefix,
                    entry_rel,
                    out_path,
                )

        async with fac() as session:
            job_final = await session.get(ExportJob, job_id)
            if job_final is None:
                return
            job_final.finished_at = datetime.now(UTC)
            if err_msg is not None:
                job_final.status = ExportStatus.failed
                job_final.error = err_msg
            else:
                job_final.status = ExportStatus.succeeded
                job_final.progress = 100
                job_final.error = None
                job_final.output_path = str(out_path.resolve())
            await session.commit()
    except Exception as e:  # noqa: BLE001
        async with fac() as session:
            job_ex = await session.get(ExportJob, job_id)
            if job_ex is None:
                return
            job_ex.status = ExportStatus.failed
            job_ex.error = str(e)[:2000]
            job_ex.finished_at = datetime.now(UTC)
            await session.commit()
