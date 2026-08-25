"""File upload -> job enqueue, job status, file listing, and the logo checker."""
from __future__ import annotations
import hashlib
import io
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from PIL import Image
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import FileRecord, AnalysisJob, AnalysisReport, Logo, User
from app.schemas import FileOut, FileWithStatusOut, ReportSummaryOut, JobOut, UploadOut, LogoOut
from app.security import get_current_user, validate_upload
from app.storage import put_object
from app.analysis_pipeline import analyze_logo
from app.celery_worker import run_analysis_task

router = APIRouter(tags=["files"])


@router.post("/files/upload", response_model=UploadOut, status_code=status.HTTP_202_ACCEPTED)
async def upload_file(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    contents = await file.read()
    mime_type = validate_upload(contents)  # magic-byte sniff + size cap; raises before queueing

    checksum = hashlib.sha256(contents).hexdigest()
    storage_key = f"orgs/{user.org_id}/uploads/{uuid.uuid4()}-{file.filename}"
    put_object(storage_key, contents, mime_type)

    record = FileRecord(
        user_id=user.id,
        org_id=user.org_id,
        storage_key=storage_key,
        original_name=file.filename or "upload",
        mime_type=mime_type,
        size_bytes=len(contents),
        checksum_sha256=checksum,
        status="ready",
    )
    db.add(record)
    db.flush()

    job = AnalysisJob(file_id=record.id, requested_by=user.id, status="queued")
    db.add(job)
    db.commit()

    # API returns immediately — the Celery worker does the actual analysis
    run_analysis_task.delay(str(job.id), storage_key, record.original_name, str(user.org_id))

    return UploadOut(file_id=record.id, job_id=job.id, status=job.status)


@router.get("/files/mine", response_model=list[FileWithStatusOut])
def list_my_files(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    records = (
        db.query(FileRecord)
        .filter_by(user_id=user.id)
        .order_by(FileRecord.created_at.desc())
        .all()
    )
    out = []
    for record in records:
        job = (
            db.query(AnalysisJob)
            .filter_by(file_id=record.id)
            .order_by(AnalysisJob.created_at.desc())
            .first()
        )
        report_summary = None
        if job and job.status == "done":
            report = db.query(AnalysisReport).filter_by(job_id=job.id).first()
            if report:
                report_summary = ReportSummaryOut(
                    id=report.id, overall_pass=report.overall_pass,
                    dpi_value=report.dpi_value, page_count=report.page_count,
                )
        out.append(FileWithStatusOut(
            **FileOut.model_validate(record).model_dump(),
            job_id=job.id if job else None,
            job_status=job.status if job else None,
            report=report_summary,
        ))
    return out


@router.get("/files/{file_id}", response_model=FileOut)
def get_file(file_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    record = db.get(FileRecord, file_id)
    # ownership check, not just JWT validity — a regular user may only see their own files
    if not record or (record.user_id != user.id and user.role != "admin"):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "File not found")
    return record


@router.get("/jobs/{job_id}", response_model=JobOut)
def get_job_status(job_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    job = db.get(AnalysisJob, job_id)
    if not job or (job.requested_by != user.id and user.role != "admin"):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found")
    return job


# ------------------------------------------------------------------
# Logo checker — standalone apparel-suitability flow
# ------------------------------------------------------------------

LOGO_RASTER_MIME = {"image/png", "image/jpeg"}
VALID_PRINT_METHODS = {"screen_print", "dtg", "sublimation", "embroidery", "unspecified"}


@router.post("/logos/check", response_model=LogoOut, status_code=status.HTTP_201_CREATED)
async def check_logo(
    file: UploadFile = File(...),
    intended_method: str = Form("unspecified"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if intended_method not in VALID_PRINT_METHODS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Invalid intended_method: {intended_method}")
    contents = await file.read()
    is_svg = (file.content_type == "image/svg+xml") or (file.filename or "").lower().endswith(".svg")

    if is_svg:
        if len(contents) > 100 * 1024 * 1024:
            raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "File exceeds 100MB limit")
        mime_type = "image/svg+xml"
        analysis = {
            "is_vector": True,
            "dpi_value": None,
            "color_count": None,
            "has_transparency": None,
            "verdict": "needs_review",
            "reasons": ["Vector file (SVG) — resolution-independent; manual color/transparency review recommended"],
        }
    else:
        mime_type = validate_upload(contents)
        if mime_type not in LOGO_RASTER_MIME:
            raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Logo must be PNG, JPEG, or SVG")
        img = Image.open(io.BytesIO(contents))
        analysis = analyze_logo(img, intended_method=intended_method)

    storage_key = f"orgs/{user.org_id}/logos/{uuid.uuid4()}-{file.filename}"
    put_object(storage_key, contents, mime_type)

    logo = Logo(
        user_id=user.id,
        org_id=user.org_id,
        storage_key=storage_key,
        original_name=file.filename or "logo",
        intended_method=intended_method,
        is_vector=analysis["is_vector"],
        dpi_value=analysis["dpi_value"],
        color_count=analysis["color_count"],
        has_transparency=analysis["has_transparency"],
        verdict=analysis["verdict"],
        reasons=analysis["reasons"],
    )
    db.add(logo)
    db.commit()
    return logo


@router.get("/logos/mine", response_model=list[LogoOut])
def list_my_logos(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return (
        db.query(Logo)
        .filter_by(user_id=user.id)
        .order_by(Logo.created_at.desc())
        .all()
    )
