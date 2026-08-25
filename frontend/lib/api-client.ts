/**
 * Typed fetch wrapper for the FastAPI backend. Handles JWT storage,
 * automatic access-token refresh on 401, and typed request/response shapes.
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const ACCESS_KEY = "qa_access_token";
const REFRESH_KEY = "qa_refresh_token";

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(ACCESS_KEY);
}

export function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(REFRESH_KEY);
}

export function setTokens(access: string, refresh: string): void {
  localStorage.setItem(ACCESS_KEY, access);
  localStorage.setItem(REFRESH_KEY, refresh);
}

export function clearTokens(): void {
  localStorage.removeItem(ACCESS_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

export function isAuthenticated(): boolean {
  return !!getAccessToken();
}

class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function tryRefresh(): Promise<boolean> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) return false;
  const res = await fetch(`${API_BASE_URL}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
  if (!res.ok) return false;
  const data = await res.json();
  setTokens(data.access_token, data.refresh_token);
  return true;
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  { retry = true, auth = true }: { retry?: boolean; auth?: boolean } = {}
): Promise<T> {
  const headers = new Headers(options.headers);
  if (!(options.body instanceof FormData) && !headers.has("Content-Type") && options.body) {
    headers.set("Content-Type", "application/json");
  }
  if (auth) {
    const token = getAccessToken();
    if (token) headers.set("Authorization", `Bearer ${token}`);
  }

  const res = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });

  if (res.status === 401 && auth && retry) {
    const refreshed = await tryRefresh();
    if (refreshed) {
      return request<T>(path, options, { retry: false, auth });
    }
    clearTokens();
  }

  if (!res.ok) {
    let message = res.statusText;
    try {
      const body = await res.json();
      message = body.detail || message;
    } catch {
      // ignore — no JSON body
    }
    throw new ApiError(res.status, message);
  }

  if (res.status === 204) return undefined as T;
  return res.json();
}

// ------------------------------------------------------------------
// Types (mirror backend/app/schemas.py)
// ------------------------------------------------------------------

export interface TokenOut {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface UserOut {
  id: string;
  org_id: string;
  email: string;
  full_name: string | null;
  role: "user" | "admin";
  is_active: boolean;
  created_at: string;
}

export interface FileOut {
  id: string;
  original_name: string;
  mime_type: string;
  size_bytes: number;
  status: string;
  created_at: string;
}

export interface ReportSummaryOut {
  id: string;
  overall_pass: boolean | null;
  dpi_value: number | null;
  page_count: number | null;
}

export interface FileWithStatusOut extends FileOut {
  job_id: string | null;
  job_status: "queued" | "running" | "done" | "failed" | null;
  report: ReportSummaryOut | null;
}

export interface JobOut {
  id: string;
  file_id: string;
  status: "queued" | "running" | "done" | "failed";
  error_message: string | null;
  retry_count: number;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
}

export interface UploadOut {
  file_id: string;
  job_id: string;
  status: string;
}

export interface FontOut {
  name: string;
  embedded: boolean;
}

export interface PaletteEntryOut {
  hex: string;
  coverage_pct: number;
}

export interface PantoneMatchOut {
  source_hex: string;
  pantone_code: string | null;
  reference_label: string | null;
  delta_e: number | null;
  confidence: number | null;
}

export interface ReportOut {
  id: string;
  job_id: string;
  file_id: string;
  page_count: number | null;
  color_mode: string | null;
  file_format: string | null;
  width_px: number | null;
  height_px: number | null;
  dpi_value: number | null;
  dpi_pass: boolean | null;
  crop_marks_present: boolean | null;
  crop_marks_pass: boolean | null;
  bleed_present: boolean | null;
  bleed_margin_mm: number | null;
  bleed_pass: boolean | null;
  white_edges_detected: boolean | null;
  white_edges_pass: boolean | null;
  fonts: FontOut[];
  color_palette: PaletteEntryOut[];
  overall_pass: boolean | null;
  pdf_report_key: string | null;
  created_at: string;
  pantone_matches: PantoneMatchOut[];
  multi_page_note: string;
}

export interface LogoOut {
  id: string;
  original_name: string;
  intended_method: string;
  is_vector: boolean | null;
  dpi_value: number | null;
  color_count: number | null;
  has_transparency: boolean | null;
  verdict: "suitable" | "unsuitable" | "needs_review" | null;
  reasons: string[];
  created_at: string;
}

export interface ThresholdsOut {
  org_id: string;
  min_dpi: number;
  min_bleed_mm: number;
  require_crop_marks: boolean;
  updated_at: string;
}

export interface AuditLogOut {
  id: string;
  actor_id: string;
  action: string;
  target_type: string;
  target_id: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
}

// ------------------------------------------------------------------
// Auth
// ------------------------------------------------------------------

export const api = {
  async signup(email: string, password: string, orgName: string, fullName?: string): Promise<TokenOut> {
    const tokens = await request<TokenOut>(
      "/auth/signup",
      { method: "POST", body: JSON.stringify({ email, password, org_name: orgName, full_name: fullName }) },
      { auth: false }
    );
    setTokens(tokens.access_token, tokens.refresh_token);
    return tokens;
  },

  async login(email: string, password: string): Promise<TokenOut> {
    const tokens = await request<TokenOut>(
      "/auth/login",
      { method: "POST", body: JSON.stringify({ email, password }) },
      { auth: false }
    );
    setTokens(tokens.access_token, tokens.refresh_token);
    return tokens;
  },

  logout(): void {
    clearTokens();
  },

  me: () => request<UserOut>("/auth/me"),

  // Files
  async uploadFile(file: File): Promise<UploadOut> {
    const form = new FormData();
    form.append("file", file);
    return request<UploadOut>("/files/upload", { method: "POST", body: form });
  },
  listMyFiles: () => request<FileWithStatusOut[]>("/files/mine"),
  getFile: (id: string) => request<FileOut>(`/files/${id}`),
  getJob: (id: string) => request<JobOut>(`/jobs/${id}`),

  // Reports
  getReportByJob: (jobId: string) => request<ReportOut>(`/reports/by-job/${jobId}`),
  getReport: (reportId: string) => request<ReportOut>(`/reports/${reportId}`),
  getReportPdfUrl: (reportId: string) => request<{ url: string }>(`/reports/${reportId}/pdf-url`),

  // Logo checker
  async checkLogo(file: File, intendedMethod: string): Promise<LogoOut> {
    const form = new FormData();
    form.append("file", file);
    form.append("intended_method", intendedMethod);
    return request<LogoOut>("/logos/check", { method: "POST", body: form });
  },
  listMyLogos: () => request<LogoOut[]>("/logos/mine"),

  // Admin
  listUsers: () => request<UserOut[]>("/admin/users"),
  setUserRole: (userId: string, role: "user" | "admin") =>
    request<UserOut>(`/admin/users/${userId}/role`, { method: "PATCH", body: JSON.stringify({ role }) }),
  deactivateUser: (userId: string) =>
    request<UserOut>(`/admin/users/${userId}/deactivate`, { method: "PATCH" }),
  reactivateUser: (userId: string) =>
    request<UserOut>(`/admin/users/${userId}/reactivate`, { method: "PATCH" }),
  getThresholds: () => request<ThresholdsOut>("/admin/thresholds"),
  updateThresholds: (body: { min_dpi: number; min_bleed_mm: number; require_crop_marks: boolean }) =>
    request<ThresholdsOut>("/admin/thresholds", { method: "PUT", body: JSON.stringify(body) }),
  listAuditLog: () => request<AuditLogOut[]>("/admin/audit-log"),
};

export { ApiError };
