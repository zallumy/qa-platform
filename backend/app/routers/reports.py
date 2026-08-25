"""Report retrieval — ownership-checked, includes pantone matches and a
presigned URL to the generated PDF report."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AnalysisJob, AnalysisReport, PantoneMatch, User
from app.schemas import ReportOut, PantoneMatchOut
from app.security import get_current_user
from app.storage import presigned_get_url

router = APIRouter(prefix="/reports", tags=["reports"])


def _build_report_out(report: AnalysisReport, db: Session) -> ReportOut:
    matches = db.query(PantoneMatch).filter_by(report_id=report.id).all()
    out = ReportOut.model_validate(report)
    out.pantone_matches = [PantoneMatchOut.model_validate(m) for m in matches]
    return out


def _load_report_for_job(job_id: str, user: User, db: Session) -> AnalysisReport:
    job = db.get(AnalysisJob, job_id)
    if not job or (job.requested_by != user.id and user.role != "admin"):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found")
    report = db.query(AnalysisReport).filter_by(job_id=job_id).first()
    if not report:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Report not ready yet")
    return report


@router.get("/by-job/{job_id}", response_model=ReportOut)
def get_report_by_job(job_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    report = _load_report_for_job(job_id, user, db)
    return _build_report_out(report, db)


@router.get("/{report_id}", response_model=ReportOut)
def get_report(report_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    report = db.get(AnalysisReport, report_id)
    if not report:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Report not found")
    job = db.get(AnalysisJob, report.job_id)
    if not job or (job.requested_by != user.id and user.role != "admin"):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Report not found")
    return _build_report_out(report, db)


@router.get("/{report_id}/pdf-url")
def get_report_pdf_url(report_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    report = db.get(AnalysisReport, report_id)
    if not report:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Report not found")
    job = db.get(AnalysisJob, report.job_id)
    if not job or (job.requested_by != user.id and user.role != "admin"):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Report not found")
    if not report.pdf_report_key:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "PDF report not generated yet")
    return {"url": presigned_get_url(report.pdf_report_key)}
