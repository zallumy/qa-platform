"""Pydantic request/response models."""
from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional, Any

from pydantic import BaseModel, EmailStr, ConfigDict, Field

# ------------------------------------------------------------------
# Auth
# ------------------------------------------------------------------

class SignupIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=200)
    org_name: str = Field(min_length=1, max_length=255)
    full_name: Optional[str] = None


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class RefreshIn(BaseModel):
    refresh_token: str


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    org_id: uuid.UUID
    email: str
    full_name: Optional[str] = None
    role: str
    is_active: bool
    created_at: datetime


# ------------------------------------------------------------------
# Files / jobs
# ------------------------------------------------------------------

class FileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    original_name: str
    mime_type: str
    size_bytes: int
    status: str
    created_at: datetime


class ReportSummaryOut(BaseModel):
    id: uuid.UUID
    overall_pass: Optional[bool] = None
    dpi_value: Optional[float] = None
    page_count: Optional[int] = None


class FileWithStatusOut(FileOut):
    job_id: Optional[uuid.UUID] = None
    job_status: Optional[str] = None
    report: Optional[ReportSummaryOut] = None


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    file_id: uuid.UUID
    status: str
    error_message: Optional[str] = None
    retry_count: int
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_at: datetime


class UploadOut(BaseModel):
    file_id: uuid.UUID
    job_id: uuid.UUID
    status: str


# ------------------------------------------------------------------
# Reports
# ------------------------------------------------------------------

class FontOut(BaseModel):
    name: str
    embedded: bool


class PaletteEntryOut(BaseModel):
    hex: str
    coverage_pct: float


class PantoneMatchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    source_hex: str
    pantone_code: Optional[str] = None
    reference_label: Optional[str] = None
    delta_e: Optional[float] = None
    confidence: Optional[float] = None


class ReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job_id: uuid.UUID
    file_id: uuid.UUID
    page_count: Optional[int] = None
    color_mode: Optional[str] = None
    file_format: Optional[str] = None
    width_px: Optional[int] = None
    height_px: Optional[int] = None
    dpi_value: Optional[float] = None
    dpi_pass: Optional[bool] = None
    crop_marks_present: Optional[bool] = None
    crop_marks_pass: Optional[bool] = None
    bleed_present: Optional[bool] = None
    bleed_margin_mm: Optional[float] = None
    bleed_pass: Optional[bool] = None
    white_edges_detected: Optional[bool] = None
    white_edges_pass: Optional[bool] = None
    fonts: list[FontOut] = []
    color_palette: list[PaletteEntryOut] = []
    overall_pass: Optional[bool] = None
    pdf_report_key: Optional[str] = None
    created_at: datetime
    pantone_matches: list[PantoneMatchOut] = []
    multi_page_note: str = (
        "v1 analyzes the first page as representative; additional pages are not yet checked."
    )


# ------------------------------------------------------------------
# Logos
# ------------------------------------------------------------------

class LogoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    original_name: str
    intended_method: str
    is_vector: Optional[bool] = None
    dpi_value: Optional[float] = None
    color_count: Optional[int] = None
    has_transparency: Optional[bool] = None
    verdict: Optional[str] = None
    reasons: list[str] = []
    created_at: datetime


# ------------------------------------------------------------------
# Admin
# ------------------------------------------------------------------

class RoleChangeIn(BaseModel):
    role: str = Field(pattern="^(user|admin)$")


class ThresholdsIn(BaseModel):
    min_dpi: float = Field(gt=0)
    min_bleed_mm: float = Field(ge=0)
    require_crop_marks: bool


class ThresholdsOut(ThresholdsIn):
    model_config = ConfigDict(from_attributes=True)
    org_id: uuid.UUID
    updated_at: datetime


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    actor_id: uuid.UUID
    action: str
    target_type: str
    target_id: Optional[uuid.UUID] = None
    metadata_json: dict[str, Any] = Field(default_factory=dict, serialization_alias="metadata")
    created_at: datetime
