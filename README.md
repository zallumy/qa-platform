# PressCheck — Print QA Check

Automated print-production QA reports for print-ready files (PDF/image), plus a standalone
apparel logo suitability checker. Multi-tenant SaaS: landing page, JWT auth with user/admin
roles, a per-user dashboard, and a full admin panel.

## Stack

- **Backend**: Python 3.12, FastAPI
- **Async workers**: Celery + Redis
- **Frontend**: Next.js (App Router) + TypeScript + Tailwind CSS
- **Database**: PostgreSQL (schema in `schema.sql`, migrated via Alembic)
- **Object storage**: MinIO locally (S3-compatible), S3 in production
- **Analysis**: PyMuPDF, Pillow, OpenCV, fontTools, colorthief

## Quick start

```bash
cp .env.example .env
# edit .env — at minimum set a real JWT_SECRET:
#   openssl rand -hex 32

docker compose up --build
```

This brings up Postgres, Redis, MinIO, runs the Alembic migration once (`migrate` service),
then starts the API, the Celery worker, and the Next.js frontend.

- Frontend: http://localhost:3000
- API: http://localhost:8000 (docs at http://localhost:8000/docs)
- MinIO console: http://localhost:9001 (login with `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD`)

No manual steps are required beyond copying `.env.example` to `.env` and filling in `JWT_SECRET`.

## Using the app

1. Sign up at `/signup` — the first person to sign up for a new organization becomes that
   org's admin.
2. Upload a PDF or image from the dashboard. The upload returns immediately; a Celery worker
   picks up the job and the file card shows `queued → running → done` as you watch (the
   dashboard polls while any job is in flight).
3. Open the full report for checklist results (DPI, crop marks, bleed, white edges, fonts and
   embedding status, color mode, dominant palette with closest-color-reference matches) and
   download the generated PDF report.
4. Try the Logo Checker for an apparel-printing suitability verdict with specific reasons.
5. As an admin, visit `/admin` to manage user roles, deactivate/reactivate accounts, edit the
   org's QA thresholds (min DPI, min bleed, require crop marks), and review the audit log —
   every mutating admin action is recorded there.

## Local development without Docker

Backend:

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export $(cat ../.env | grep -v '^#' | xargs)   # or set the vars manually
alembic upgrade head
uvicorn app.main:app --reload
```

Celery worker (separate terminal, same env vars):

```bash
celery -A app.celery_worker worker --loglevel=info --concurrency=4
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

You'll still need Postgres, Redis, and MinIO running somewhere reachable — the simplest way is
`docker compose up postgres redis minio`.

## Production deployment

`docker-compose.prod.yml` + `deploy/Caddyfile` deploy the same stack behind Caddy (automatic
HTTPS), with Postgres/Redis/MinIO kept off the public internet — only Caddy publishes ports
80/443. See the step-by-step deployment walkthrough for provisioning a server, DNS, and running
this in production.

## Notable design decisions / limitations (v1)

- **First-page-only analysis for PDFs.** A multi-page PDF is analyzed using its first page as
  representative; this is called out in the report UI (`multi_page_note`), not hidden.
- **Pantone matching is an open approximation**, not the licensed Pantone Connect API. Matches
  are shown as "closest color reference" — never labeled "Pantone®" anywhere in the UI or PDF
  report. See `backend/app/color_reference.py` and `match_pantone_approx` in
  `backend/app/analysis_pipeline.py`; swap both for the licensed API when available.
  `pantone_matches.pantone_code` is left `NULL` until then. The Delta-E approximation uses a
  real sRGB→CIE Lab conversion (CIE76 distance), replacing the seed's RGB-Euclidean placeholder.
- **Non-embedded fonts are treated as a hard fail** — they roll into `overall_pass` and are
  flagged explicitly in both the web report and the generated PDF.
- **File validation** happens before anything reaches the analysis queue: real MIME-byte
  sniffing (`python-magic`, not just the file extension) and a 100MB size cap.
- **Tenant isolation**: every query is scoped by `org_id`/`user_id`, and file/report/job access
  is checked by ownership (or admin role), not just by having a valid JWT. Row-Level Security is
  also enabled at the DB layer on `files` and `logos` (see `schema.sql`) as defense in depth.
- **Logo checker** accepts PNG/JPEG (fully analyzed) and SVG (accepted as vector; flagged
  `needs_review` since resolution/transparency don't apply the same way to vector art).
- Out of scope for v1, per the build brief: licensed Pantone API, SSO/social login, Kubernetes
  manifests, and multi-page-aware analysis.

## Repo structure

```
/backend
  /app                 FastAPI app, models, schemas, analysis pipeline, Celery worker
    /routers           auth, files (+ logo checker), reports, admin
  /migrations          Alembic migrations (generated from schema.sql)
/frontend
  /app                 Next.js App Router pages (marketing, auth, dashboard, admin)
  /components          Shared design-system components (registration-mark motif, etc.)
  /lib                 Typed API client + auth hook
schema.sql              Canonical Postgres schema — source of truth for migrations/models
docker-compose.yml       postgres, redis, minio, api, worker, frontend
.env.example
```

## Testing tenant isolation / admin authorization

There's no automated test suite checked in yet. To manually verify the two hard requirements
from the build brief:

- **Cross-tenant file/report access**: sign up two separate orgs, upload a file as user A, then
  try `GET /files/{id}`, `/jobs/{id}`, `/reports/{id}` as user B — each should 404, not 403,
  to avoid confirming the resource exists.
- **Admin-only routes**: call any `/admin/*` route as a non-admin user — expect `403`.
