"""Initial schema — generated 1:1 from schema.sql

Revision ID: 0001
Revises:
Create Date: 2026-08-25

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

# The exact contents of schema.sql (repo root), executed verbatim so the
# migration and the checked-in schema can never drift apart.
SCHEMA_SQL = r"""
-- ============================================================
-- Print QA Check Application — PostgreSQL Schema
-- ============================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "citext";

-- ------------------------------------------------------------
-- ENUM TYPES
-- ------------------------------------------------------------

CREATE TYPE user_role AS ENUM ('user', 'admin');

CREATE TYPE job_status AS ENUM ('queued', 'running', 'done', 'failed');

CREATE TYPE file_status AS ENUM ('uploaded', 'validating', 'ready', 'rejected');

CREATE TYPE logo_verdict AS ENUM ('suitable', 'unsuitable', 'needs_review');

CREATE TYPE print_method AS ENUM ('screen_print', 'dtg', 'sublimation', 'embroidery', 'unspecified');

-- ------------------------------------------------------------
-- ORGANIZATIONS  (tenants)
-- ------------------------------------------------------------

CREATE TABLE organizations (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name            VARCHAR(255) NOT NULL,
    plan            VARCHAR(50) NOT NULL DEFAULT 'free',
    settings        JSONB NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ------------------------------------------------------------
-- USERS
-- ------------------------------------------------------------

CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id          UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    email           CITEXT NOT NULL UNIQUE,
    password_hash   TEXT NOT NULL,
    full_name       VARCHAR(255),
    role            user_role NOT NULL DEFAULT 'user',
    is_active       BOOLEAN NOT NULL DEFAULT true,
    email_verified  BOOLEAN NOT NULL DEFAULT false,
    last_login_at   TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_users_org_id ON users(org_id);
CREATE INDEX idx_users_role ON users(role);

-- ------------------------------------------------------------
-- REFRESH TOKENS  (rotating JWT refresh tokens)
-- ------------------------------------------------------------

CREATE TABLE refresh_tokens (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash      TEXT NOT NULL,
    expires_at      TIMESTAMPTZ NOT NULL,
    revoked_at      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_refresh_tokens_user_id ON refresh_tokens(user_id);

-- ------------------------------------------------------------
-- FILES  (uploaded PDFs / images to be QA-checked)
-- ------------------------------------------------------------

CREATE TABLE files (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    org_id          UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    storage_key     TEXT NOT NULL,
    original_name   VARCHAR(500) NOT NULL,
    mime_type       VARCHAR(100) NOT NULL,
    size_bytes      BIGINT NOT NULL,
    status          file_status NOT NULL DEFAULT 'uploaded',
    checksum_sha256 CHAR(64),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_files_user_id ON files(user_id);
CREATE INDEX idx_files_org_id ON files(org_id);
CREATE INDEX idx_files_status ON files(status);

-- ------------------------------------------------------------
-- ANALYSIS JOBS  (one per file analysis run)
-- ------------------------------------------------------------

CREATE TABLE analysis_jobs (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    file_id         UUID NOT NULL REFERENCES files(id) ON DELETE CASCADE,
    requested_by    UUID NOT NULL REFERENCES users(id),
    status          job_status NOT NULL DEFAULT 'queued',
    error_message   TEXT,
    retry_count     INT NOT NULL DEFAULT 0,
    started_at      TIMESTAMPTZ,
    finished_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_analysis_jobs_file_id ON analysis_jobs(file_id);
CREATE INDEX idx_analysis_jobs_status ON analysis_jobs(status);

-- ------------------------------------------------------------
-- ANALYSIS REPORTS  (results of a completed job)
-- ------------------------------------------------------------

CREATE TABLE analysis_reports (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id              UUID NOT NULL REFERENCES analysis_jobs(id) ON DELETE CASCADE,
    file_id             UUID NOT NULL REFERENCES files(id) ON DELETE CASCADE,

    page_count          INT,
    color_mode          VARCHAR(20),
    file_format         VARCHAR(20),
    width_px            INT,
    height_px           INT,

    dpi_value           NUMERIC(6,2),
    dpi_pass            BOOLEAN,
    crop_marks_present  BOOLEAN,
    crop_marks_pass     BOOLEAN,
    bleed_present        BOOLEAN,
    bleed_margin_mm     NUMERIC(5,2),
    bleed_pass          BOOLEAN,
    white_edges_detected BOOLEAN,
    white_edges_pass    BOOLEAN,

    fonts               JSONB NOT NULL DEFAULT '[]',
    color_palette        JSONB NOT NULL DEFAULT '[]',

    overall_pass        BOOLEAN,
    pdf_report_key      TEXT,

    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_analysis_reports_job_id ON analysis_reports(job_id);
CREATE INDEX idx_analysis_reports_file_id ON analysis_reports(file_id);

-- ------------------------------------------------------------
-- PANTONE MATCHES  (linked to a report's extracted palette)
-- ------------------------------------------------------------

CREATE TABLE pantone_matches (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    report_id       UUID NOT NULL REFERENCES analysis_reports(id) ON DELETE CASCADE,
    source_hex      CHAR(7) NOT NULL,
    pantone_code    VARCHAR(30),
    reference_label VARCHAR(100),
    delta_e         NUMERIC(6,3),
    confidence      NUMERIC(4,3),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_pantone_matches_report_id ON pantone_matches(report_id);

-- ------------------------------------------------------------
-- LOGOS  (separate upload flow for apparel-suitability checks)
-- ------------------------------------------------------------

CREATE TABLE logos (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    org_id              UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    storage_key         TEXT NOT NULL,
    original_name       VARCHAR(500) NOT NULL,
    intended_method     print_method NOT NULL DEFAULT 'unspecified',
    is_vector           BOOLEAN,
    dpi_value           NUMERIC(6,2),
    color_count         INT,
    has_transparency    BOOLEAN,
    verdict             logo_verdict,
    reasons             JSONB NOT NULL DEFAULT '[]',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_logos_user_id ON logos(user_id);
CREATE INDEX idx_logos_org_id ON logos(org_id);

-- ------------------------------------------------------------
-- AUDIT LOG  (admin accountability — every mutating admin action)
-- ------------------------------------------------------------

CREATE TABLE audit_log (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    actor_id        UUID NOT NULL REFERENCES users(id),
    action          VARCHAR(100) NOT NULL,
    target_type     VARCHAR(50) NOT NULL,
    target_id       UUID,
    metadata        JSONB NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_audit_log_actor_id ON audit_log(actor_id);
CREATE INDEX idx_audit_log_target ON audit_log(target_type, target_id);

-- ------------------------------------------------------------
-- ORG-LEVEL QA THRESHOLDS  (admin-editable defaults, e.g. min DPI)
-- ------------------------------------------------------------

CREATE TABLE qa_thresholds (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id          UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    min_dpi         NUMERIC(6,2) NOT NULL DEFAULT 300.00,
    min_bleed_mm    NUMERIC(5,2) NOT NULL DEFAULT 3.00,
    require_crop_marks BOOLEAN NOT NULL DEFAULT true,
    updated_by      UUID REFERENCES users(id),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (org_id)
);

-- ------------------------------------------------------------
-- updated_at auto-touch trigger (reusable)
-- ------------------------------------------------------------

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_files_updated_at BEFORE UPDATE ON files
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_organizations_updated_at BEFORE UPDATE ON organizations
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ------------------------------------------------------------
-- Row-Level Security (optional hardening — enforce tenant isolation
-- at the DB layer in addition to the application layer)
-- ------------------------------------------------------------

ALTER TABLE files ENABLE ROW LEVEL SECURITY;
ALTER TABLE logos ENABLE ROW LEVEL SECURITY;

-- Example policy (app sets `app.current_user_id` / `app.current_org_id` per session):
-- CREATE POLICY files_tenant_isolation ON files
--     USING (org_id = current_setting('app.current_org_id')::uuid);
"""

DOWNGRADE_SQL = r"""
DROP TABLE IF EXISTS qa_thresholds CASCADE;
DROP TABLE IF EXISTS audit_log CASCADE;
DROP TABLE IF EXISTS logos CASCADE;
DROP TABLE IF EXISTS pantone_matches CASCADE;
DROP TABLE IF EXISTS analysis_reports CASCADE;
DROP TABLE IF EXISTS analysis_jobs CASCADE;
DROP TABLE IF EXISTS files CASCADE;
DROP TABLE IF EXISTS refresh_tokens CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS organizations CASCADE;

DROP FUNCTION IF EXISTS set_updated_at() CASCADE;

DROP TYPE IF EXISTS print_method;
DROP TYPE IF EXISTS logo_verdict;
DROP TYPE IF EXISTS file_status;
DROP TYPE IF EXISTS job_status;
DROP TYPE IF EXISTS user_role;
"""


def upgrade() -> None:
    op.execute(SCHEMA_SQL)


def downgrade() -> None:
    op.execute(DOWNGRADE_SQL)
