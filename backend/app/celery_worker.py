"""
Print QA Check Application — Celery worker
============================================
Runs the analysis pipeline off the request/response cycle. Scale this
process horizontally and independently from the FastAPI app — this is
where the actual CPU cost of the product lives.

Run with:
    celery -A app.celery_worker worker --loglevel=info --concurrency=4
"""

from __future__ import annotations
import io
import os
import uuid
from datetime import datetime, timezone

from celery import Celery
from celery.utils.log import get_task_logger

from app.database import SessionLocal
from app.models import AnalysisJob, AnalysisReport, PantoneMatch, QAThresholds
from app.storage import get_object, put_object, ensure_bucket
from app.analysis_pipeline import run_analysis_pipeline, match_pantone_approx, ReportResult, DEFAULT_MIN_DPI, DEFAULT_MIN_BLEED_MM

ensure_bucket()

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery("qa_worker", broker=REDIS_URL, backend=REDIS_URL)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_acks_late=True,           # don't lose jobs if a worker dies mid-analysis
    worker_prefetch_multiplier=1,  # analysis jobs are heavy; don't over-batch per worker
    task_time_limit=600,           # hard kill runaway jobs (10 min)
    task_soft_time_limit=540,
)

log = get_task_logger(__name__)

MAX_RETRIES = 3


def _org_thresholds(db, org_id: str) -> tuple[float, float]:
    row = db.query(QAThresholds).filter_by(org_id=org_id).first()
    if not row:
        return DEFAULT_MIN_DPI, DEFAULT_MIN_BLEED_MM
    return float(row.min_dpi), float(row.min_bleed_mm)


@celery_app.task(bind=True, max_retries=MAX_RETRIES, default_retry_delay=30)
def run_analysis_task(self, job_id: str, storage_key: str, filename: str, org_id: str):
    """
    1. Mark job 'running'
    2. Download file from S3/MinIO
    3. Run the analysis pipeline (thresholds loaded from the org's qa_thresholds row)
    4. Write analysis_reports + pantone_matches rows, generate PDF report
    5. Mark job 'done' (or 'failed' after retries exhausted)
    """
    db = SessionLocal()
    try:
        job = db.get(AnalysisJob, job_id)
        if job is None:
            log.error(f"Job {job_id} not found — skipping")
            return
        job.status = "running"
        job.started_at = datetime.now(timezone.utc)
        db.commit()

        file_bytes = get_object(storage_key)
        min_dpi, min_bleed_mm = _org_thresholds(db, org_id)

        result: ReportResult = run_analysis_pipeline(
            file_bytes, filename, min_dpi=min_dpi, min_bleed_mm=min_bleed_mm,
        )

        report = AnalysisReport(
            id=uuid.uuid4(),
            job_id=job_id,
            file_id=job.file_id,
            page_count=result.page_count,
            color_mode=result.color_mode,
            file_format=result.file_format,
            width_px=result.width_px,
            height_px=result.height_px,
            dpi_value=result.dpi_value,
            dpi_pass=result.dpi_pass,
            crop_marks_present=result.crop_marks_present,
            crop_marks_pass=result.crop_marks_pass,
            bleed_present=result.bleed_present,
            bleed_margin_mm=result.bleed_margin_mm,
            bleed_pass=result.bleed_pass,
            white_edges_detected=result.white_edges_detected,
            white_edges_pass=result.white_edges_pass,
            fonts=result.fonts,
            color_palette=result.color_palette,
            overall_pass=result.overall_pass,
        )
        db.add(report)
        db.flush()

        for entry in result.color_palette:
            match = match_pantone_approx(entry["hex"])
            db.add(PantoneMatch(
                report_id=report.id,
                source_hex=entry["hex"],
                pantone_code=match["pantone_code"],
                reference_label=match["reference_label"],
                delta_e=match["delta_e"],
                confidence=match["confidence"],
            ))

        pdf_key = _generate_pdf_report(report, filename)
        report.pdf_report_key = pdf_key

        job.status = "done"
        job.finished_at = datetime.now(timezone.utc)
        db.commit()
        log.info(f"Analysis complete for job {job_id}: overall_pass={result.overall_pass}")

    except Exception as exc:
        db.rollback()
        log.error(f"Analysis failed for job {job_id}: {exc}")
        job = db.get(AnalysisJob, job_id)
        if job is not None:
            job.retry_count = (job.retry_count or 0) + 1
            job.error_message = str(exc)

            if self.request.retries < MAX_RETRIES:
                job.status = "queued"
                db.commit()
                raise self.retry(exc=exc)
            else:
                job.status = "failed"
                db.commit()
    finally:
        db.close()


# ------------------------------------------------------------------
# PDF report generation — paper/ink/registration-blue design language
# ------------------------------------------------------------------

_INK = (0.12, 0.12, 0.12)
_REG_BLUE = (0.13, 0.31, 0.60)  # ~#24519C, matches the dashboard design system
_PASS_GREEN = (0.0, 0.44, 0.32)
_FAIL_RED = (0.70, 0.06, 0.06)


def _generate_pdf_report(report: AnalysisReport, filename: str) -> str:
    import fitz  # PyMuPDF can also author simple PDFs

    doc = fitz.open()
    page = doc.new_page()
    width = page.rect.width

    # header band
    page.draw_rect(fitz.Rect(0, 0, width, 70), color=_REG_BLUE, fill=_REG_BLUE)
    page.insert_text((50, 30), "PRINT QA REPORT", fontsize=16, color=(1, 1, 1), fontname="helv")
    page.insert_text((50, 50), filename, fontsize=10, color=(1, 1, 1), fontname="helv")

    y = 100
    verdict = "PASS" if report.overall_pass else "FAIL"
    verdict_color = _PASS_GREEN if report.overall_pass else _FAIL_RED
    page.insert_text((50, y), f"Overall: {verdict}", fontsize=13, color=verdict_color, fontname="helv")
    y += 30

    def row(label: str, value: str, passed: bool | None = None):
        nonlocal y
        marker = "PASS" if passed else ("FAIL" if passed is False else "—")
        color = _PASS_GREEN if passed else (_FAIL_RED if passed is False else _INK)
        page.insert_text((50, y), f"{label}", fontsize=11, color=_INK, fontname="helv")
        page.insert_text((260, y), f"{value}", fontsize=11, color=_INK, fontname="helv")
        page.insert_text((450, y), marker, fontsize=11, color=color, fontname="helv")
        y += 20

    row("DPI / Resolution", f"{report.dpi_value or 'n/a'} dpi", report.dpi_pass)
    row("Crop marks", "present" if report.crop_marks_present else "missing", report.crop_marks_pass)
    row("Bleed", f"{report.bleed_margin_mm or 'n/a'} mm", report.bleed_pass)
    row("White edges", "detected" if report.white_edges_detected else "none", report.white_edges_pass)

    non_embedded = [f["name"] for f in (report.fonts or []) if not f.get("embedded")]
    row("Fonts embedded", f"{len(report.fonts or [])} font(s), {len(non_embedded)} not embedded",
        len(non_embedded) == 0)

    y += 10
    page.insert_text((50, y), f"Pages: {report.page_count}  |  Color mode: {report.color_mode}  |  "
                               f"Format: {report.file_format}", fontsize=10, color=_INK, fontname="helv")
    y += 20
    if non_embedded:
        page.insert_text((50, y), f"Non-embedded fonts (hard-fail): {', '.join(non_embedded)}",
                          fontsize=10, color=_FAIL_RED, fontname="helv")
        y += 20

    y += 10
    page.insert_text((50, y), "Dominant color palette (closest color reference — not licensed Pantone):",
                      fontsize=10, color=_INK, fontname="helv")
    y += 15
    for entry in (report.color_palette or []):
        hexcode = entry["hex"]
        rgb = tuple(int(hexcode.lstrip("#")[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
        page.draw_rect(fitz.Rect(50, y, 65, y + 12), color=rgb, fill=rgb)
        page.insert_text((72, y + 10), f"{hexcode}  ({entry['coverage_pct']}% coverage)",
                          fontsize=9, color=_INK, fontname="helv")
        y += 18

    y += 10
    page.insert_text(
        (50, y),
        "Note: v1 analyzes the first page as representative; additional pages are not yet checked.",
        fontsize=8, color=(0.4, 0.4, 0.4), fontname="helv",
    )

    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    key = f"reports/{report.id}.pdf"
    put_object(key, buf.getvalue(), "application/pdf")
    return key
