"""
SQLAlchemy ORM models — mirrors schema.sql 1:1.

This is the single source of truth for the ORM layer. Import from here in
both the API and the worker; do not redefine models inline anywhere else.
"""
from __future__ import annotations
import uuid

from sqlalchemy import (
    Column, String, Boolean, DateTime, ForeignKey, Enum, Integer,
    BigInteger, Numeric, Text, CHAR, VARCHAR, UniqueConstraint, Index,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB, CITEXT
from sqlalchemy.orm import relationship

from app.database import Base

# ------------------------------------------------------------------
# ENUM TYPES (mirror schema.sql CREATE TYPE ... AS ENUM)
# ------------------------------------------------------------------

UserRole = Enum("user", "admin", name="user_role")
JobStatus = Enum("queued", "running", "done", "failed", name="job_status")
FileStatus = Enum("uploaded", "validating", "ready", "rejected", name="file_status")
LogoVerdict = Enum("suitable", "unsuitable", "needs_review", name="logo_verdict")
PrintMethod = Enum(
    "screen_print", "dtg", "sublimation", "embroidery", "unspecified",
    name="print_method",
)


def _uuid_col(**kw):
    return Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, **kw)


# ------------------------------------------------------------------
# ORGANIZATIONS (tenants)
# ------------------------------------------------------------------

class Organization(Base):
    __tablename__ = "organizations"

    id = _uuid_col()
    name = Column(VARCHAR(255), nullable=False)
    plan = Column(VARCHAR(50), nullable=False, default="free", server_default="free")
    settings = Column(JSONB, nullable=False, default=dict, server_default="{}")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    users = relationship("User", back_populates="organization", cascade="all, delete-orphan")


# ------------------------------------------------------------------
# USERS
# ------------------------------------------------------------------

class User(Base):
    __tablename__ = "users"

    id = _uuid_col()
    org_id = Column(PG_UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"),
                     nullable=False, index=True)
    email = Column(CITEXT, nullable=False, unique=True)
    password_hash = Column(Text, nullable=False)
    full_name = Column(VARCHAR(255))
    role = Column(UserRole, nullable=False, default="user", server_default="user", index=True)
    is_active = Column(Boolean, nullable=False, default=True, server_default="true")
    email_verified = Column(Boolean, nullable=False, default=False, server_default="false")
    last_login_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    organization = relationship("Organization", back_populates="users")


# ------------------------------------------------------------------
# REFRESH TOKENS (rotating JWT refresh tokens)
# ------------------------------------------------------------------

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = _uuid_col()
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
                      nullable=False, index=True)
    token_hash = Column(Text, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


# ------------------------------------------------------------------
# FILES (uploaded PDFs / images to be QA-checked)
# ------------------------------------------------------------------

class FileRecord(Base):
    __tablename__ = "files"

    id = _uuid_col()
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
                      nullable=False, index=True)
    org_id = Column(PG_UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"),
                     nullable=False, index=True)
    storage_key = Column(Text, nullable=False)
    original_name = Column(VARCHAR(500), nullable=False)
    mime_type = Column(VARCHAR(100), nullable=False)
    size_bytes = Column(BigInteger, nullable=False)
    status = Column(FileStatus, nullable=False, default="uploaded", server_default="uploaded", index=True)
    checksum_sha256 = Column(CHAR(64))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


# ------------------------------------------------------------------
# ANALYSIS JOBS (one per file analysis run)
# ------------------------------------------------------------------

class AnalysisJob(Base):
    __tablename__ = "analysis_jobs"

    id = _uuid_col()
    file_id = Column(PG_UUID(as_uuid=True), ForeignKey("files.id", ondelete="CASCADE"),
                      nullable=False, index=True)
    requested_by = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    status = Column(JobStatus, nullable=False, default="queued", server_default="queued", index=True)
    error_message = Column(Text)
    retry_count = Column(Integer, nullable=False, default=0, server_default="0")
    started_at = Column(DateTime(timezone=True))
    finished_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


# ------------------------------------------------------------------
# ANALYSIS REPORTS (results of a completed job)
# ------------------------------------------------------------------

class AnalysisReport(Base):
    __tablename__ = "analysis_reports"

    id = _uuid_col()
    job_id = Column(PG_UUID(as_uuid=True), ForeignKey("analysis_jobs.id", ondelete="CASCADE"),
                     nullable=False, index=True)
    file_id = Column(PG_UUID(as_uuid=True), ForeignKey("files.id", ondelete="CASCADE"),
                      nullable=False, index=True)

    # file info
    page_count = Column(Integer)
    color_mode = Column(VARCHAR(20))
    file_format = Column(VARCHAR(20))
    width_px = Column(Integer)
    height_px = Column(Integer)

    # quality checks
    dpi_value = Column(Numeric(6, 2))
    dpi_pass = Column(Boolean)
    crop_marks_present = Column(Boolean)
    crop_marks_pass = Column(Boolean)
    bleed_present = Column(Boolean)
    bleed_margin_mm = Column(Numeric(5, 2))
    bleed_pass = Column(Boolean)
    white_edges_detected = Column(Boolean)
    white_edges_pass = Column(Boolean)

    # rich data
    fonts = Column(JSONB, nullable=False, default=list, server_default="[]")
    color_palette = Column(JSONB, nullable=False, default=list, server_default="[]")

    overall_pass = Column(Boolean)
    pdf_report_key = Column(Text)

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


# ------------------------------------------------------------------
# PANTONE MATCHES (linked to a report's extracted palette)
# ------------------------------------------------------------------

class PantoneMatch(Base):
    __tablename__ = "pantone_matches"

    id = _uuid_col()
    report_id = Column(PG_UUID(as_uuid=True), ForeignKey("analysis_reports.id", ondelete="CASCADE"),
                        nullable=False, index=True)
    source_hex = Column(CHAR(7), nullable=False)
    pantone_code = Column(VARCHAR(30))
    reference_label = Column(VARCHAR(100))
    delta_e = Column(Numeric(6, 3))
    confidence = Column(Numeric(4, 3))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


# ------------------------------------------------------------------
# LOGOS (separate upload flow for apparel-suitability checks)
# ------------------------------------------------------------------

class Logo(Base):
    __tablename__ = "logos"

    id = _uuid_col()
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
                      nullable=False, index=True)
    org_id = Column(PG_UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"),
                     nullable=False, index=True)
    storage_key = Column(Text, nullable=False)
    original_name = Column(VARCHAR(500), nullable=False)
    intended_method = Column(PrintMethod, nullable=False, default="unspecified", server_default="unspecified")
    is_vector = Column(Boolean)
    dpi_value = Column(Numeric(6, 2))
    color_count = Column(Integer)
    has_transparency = Column(Boolean)
    verdict = Column(LogoVerdict)
    reasons = Column(JSONB, nullable=False, default=list, server_default="[]")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


# ------------------------------------------------------------------
# AUDIT LOG (admin accountability — every mutating admin action)
# ------------------------------------------------------------------

class AuditLog(Base):
    __tablename__ = "audit_log"

    id = _uuid_col()
    actor_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    action = Column(VARCHAR(100), nullable=False)
    target_type = Column(VARCHAR(50), nullable=False)
    target_id = Column(PG_UUID(as_uuid=True))
    # mapped to the `metadata` column under a different attribute name —
    # `metadata` is reserved on declarative Base for the schema MetaData object.
    metadata_json = Column("metadata", JSONB, nullable=False, default=dict, server_default="{}")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        Index("idx_audit_log_target", "target_type", "target_id"),
    )


# ------------------------------------------------------------------
# ORG-LEVEL QA THRESHOLDS (admin-editable defaults, e.g. min DPI)
# ------------------------------------------------------------------

class QAThresholds(Base):
    __tablename__ = "qa_thresholds"

    id = _uuid_col()
    org_id = Column(PG_UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"),
                     nullable=False, unique=True)
    min_dpi = Column(Numeric(6, 2), nullable=False, default=300, server_default="300.00")
    min_bleed_mm = Column(Numeric(5, 2), nullable=False, default=3, server_default="3.00")
    require_crop_marks = Column(Boolean, nullable=False, default=True, server_default="true")
    updated_by = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"))
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
