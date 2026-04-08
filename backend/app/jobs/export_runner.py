from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.config import get_settings
from app.db.models.export_job import ExportJob, ExportStatus
from app.db.session import session_factory


async def run_export_job(job_id: uuid.UUID) -> None:
    fac = session_factory()
    async with fac() as session:
        job = await session.get(ExportJob, job_id)
        if job is None:
            return
        job.status = ExportStatus.running
        job.started_at = datetime.now(UTC)
        job.progress = 10
        await session.commit()

    try:
        settings = get_settings()
        out_dir = settings.storage_root / "exports"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{job_id}.pdf"
        out_path.write_bytes(
            b"%PDF-1.3\n1 0 obj<<>>endobj trailer<<>>\n%%EOF\n",
        )
        async with fac() as session:
            job2 = await session.get(ExportJob, job_id)
            if job2 is None:
                return
            job2.status = ExportStatus.succeeded
            job2.progress = 100
            job2.output_path = str(out_path.resolve())
            job2.finished_at = datetime.now(UTC)
            await session.commit()
    except Exception as e:  # noqa: BLE001
        async with fac() as session:
            job3 = await session.get(ExportJob, job_id)
            if job3 is None:
                return
            job3.status = ExportStatus.failed
            job3.error = str(e)[:2000]
            job3.finished_at = datetime.now(UTC)
            await session.commit()
