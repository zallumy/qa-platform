"""
Print QA Check Application — Analysis Pipeline
================================================
Runs as a Celery task. Orchestrates all checks in the QA checklist and
writes results matching the `analysis_reports` schema.

v1 limitation: PDFs are analyzed on their first page only, as representative
of the document. This is surfaced in the report UI, not hidden.
"""

from __future__ import annotations
import io
import math
from dataclasses import dataclass, field
from typing import Optional

import fitz  # PyMuPDF
import numpy as np
from PIL import Image
import cv2
from colorthief import ColorThief

from app.color_reference import REFERENCE_COLORS

# ------------------------------------------------------------------
# Config defaults (overridden per-request from the org's qa_thresholds row)
# ------------------------------------------------------------------

DEFAULT_MIN_DPI = 300.0
DEFAULT_MIN_BLEED_MM = 3.0
MM_PER_INCH = 25.4


@dataclass
class ReportResult:
    page_count: int = 0
    color_mode: str = ""
    file_format: str = ""
    width_px: int = 0
    height_px: int = 0

    dpi_value: Optional[float] = None
    dpi_pass: Optional[bool] = None

    crop_marks_present: bool = False
    crop_marks_pass: bool = False

    bleed_present: bool = False
    bleed_margin_mm: Optional[float] = None
    bleed_pass: bool = False

    white_edges_detected: bool = False
    white_edges_pass: bool = True

    fonts: list = field(default_factory=list)          # [{name, embedded}]
    color_palette: list = field(default_factory=list)   # [{hex, coverage_pct}]

    overall_pass: bool = False


# ------------------------------------------------------------------
# Entry point (Celery task)
# ------------------------------------------------------------------

def run_analysis_pipeline(file_bytes: bytes, filename: str,
                           min_dpi: float = DEFAULT_MIN_DPI,
                           min_bleed_mm: float = DEFAULT_MIN_BLEED_MM) -> ReportResult:
    """Main orchestrator. Dispatches to PDF or raster-image pipeline."""
    is_pdf = filename.lower().endswith(".pdf")
    result = ReportResult()

    if is_pdf:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        result.file_format = "PDF"
        result.page_count = doc.page_count
        page = doc[0]  # analyze first page as representative; see v1 limitation note above

        result.width_px, result.height_px, dpi = _pdf_effective_dpi(page)
        result.dpi_value = dpi
        result.dpi_pass = dpi is not None and dpi >= min_dpi

        result.crop_marks_present = _pdf_has_crop_marks(page)
        result.crop_marks_pass = result.crop_marks_present

        bleed_mm, has_bleed = _pdf_bleed_margin(page)
        result.bleed_margin_mm = bleed_mm
        result.bleed_present = has_bleed
        result.bleed_pass = has_bleed and bleed_mm is not None and bleed_mm >= min_bleed_mm

        result.fonts = _pdf_fonts(doc)

        # rasterize page for pixel-level checks (white edges, palette, color mode)
        pix = page.get_pixmap(dpi=150)
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        result.color_mode = _detect_color_mode(doc, page)
        doc.close()

    else:
        img = Image.open(io.BytesIO(file_bytes))
        result.file_format = img.format or "IMAGE"
        result.page_count = 1
        result.width_px, result.height_px = img.size
        result.color_mode = img.mode
        result.dpi_value = _image_dpi(img)
        result.dpi_pass = result.dpi_value is not None and result.dpi_value >= min_dpi
        # crop marks / bleed are PDF-box concepts; for flat images, only heuristic edge checks apply
        result.crop_marks_present = _image_has_crop_marks(img)
        result.crop_marks_pass = result.crop_marks_present
        result.bleed_pass = True  # not applicable without trim/bleed boxes; flagged as N/A upstream
        result.fonts = []

    result.white_edges_detected = _detect_white_edges(img)
    result.white_edges_pass = not result.white_edges_detected
    result.color_palette = _extract_palette(img)

    result.overall_pass = all([
        result.dpi_pass,
        result.crop_marks_pass or result.file_format != "PDF",  # only enforced where applicable
        result.bleed_pass,
        result.white_edges_pass,
        _fonts_all_embedded(result.fonts),  # non-embedded fonts are a hard-fail signal
    ])

    return result


def _fonts_all_embedded(fonts: list[dict]) -> bool:
    return all(f.get("embedded") for f in fonts) if fonts else True


# ------------------------------------------------------------------
# DPI
# ------------------------------------------------------------------

def _image_dpi(img: Image.Image) -> Optional[float]:
    dpi = img.info.get("dpi")
    if dpi:
        return round(float(dpi[0]), 2)
    return None  # caller should prompt user for intended print size to compute effective DPI


def _pdf_effective_dpi(page: fitz.Page) -> tuple[int, int, Optional[float]]:
    """Effective DPI = placed image pixel width / page width in inches."""
    images = page.get_images(full=True)
    if not images:
        return 0, 0, None
    xref = images[0][0]
    base = page.parent.extract_image(xref)
    pil_img = Image.open(io.BytesIO(base["image"]))
    w_px, h_px = pil_img.size
    page_width_in = page.rect.width / 72.0  # PDF units are 1/72 inch
    dpi = round(w_px / page_width_in, 2) if page_width_in else None
    return w_px, h_px, dpi


# ------------------------------------------------------------------
# Crop marks
# ------------------------------------------------------------------

def _pdf_has_crop_marks(page: fitz.Page) -> bool:
    """Check for registration/crop-mark drawing objects near the TrimBox corners."""
    trim = page.trimbox or page.rect
    drawings = page.get_drawings()
    corner_zone = 20  # points
    corners = [
        (trim.x0, trim.y0), (trim.x1, trim.y0),
        (trim.x0, trim.y1), (trim.x1, trim.y1),
    ]
    hits = 0
    for d in drawings:
        r = d["rect"]
        for cx, cy in corners:
            if abs(r.x0 - cx) < corner_zone or abs(r.x1 - cx) < corner_zone:
                if abs(r.y0 - cy) < corner_zone or abs(r.y1 - cy) < corner_zone:
                    hits += 1
                    break
    return hits >= 2  # at least 2 corners marked = likely real crop marks


def _image_has_crop_marks(img: Image.Image) -> bool:
    """Heuristic: look for thin dark line segments in the outer border region via OpenCV."""
    arr = np.array(img.convert("L"))
    h, w = arr.shape
    border = max(20, int(min(h, w) * 0.03))
    edges = cv2.Canny(arr, 50, 150)
    corner_regions = [
        edges[:border, :border], edges[:border, -border:],
        edges[-border:, :border], edges[-border:, -border:],
    ]
    hits = sum(1 for region in corner_regions if region.sum() > 0)
    return hits >= 2


# ------------------------------------------------------------------
# Bleed
# ------------------------------------------------------------------

def _pdf_bleed_margin(page: fitz.Page) -> tuple[Optional[float], bool]:
    trim = page.trimbox
    bleed = getattr(page, "bleedbox", None)
    if not trim or not bleed:
        return None, False
    margin_pt = min(
        trim.x0 - bleed.x0, bleed.x1 - trim.x1,
        trim.y0 - bleed.y0, bleed.y1 - trim.y1,
    )
    margin_mm = round(margin_pt * (MM_PER_INCH / 72.0), 2)
    return margin_mm, margin_mm > 0


# ------------------------------------------------------------------
# White edges
# ------------------------------------------------------------------

def _detect_white_edges(img: Image.Image, band_pct: float = 0.03, threshold: int = 245) -> bool:
    arr = np.array(img.convert("L"))
    h, w = arr.shape
    band = max(2, int(min(h, w) * band_pct))
    border_pixels = np.concatenate([
        arr[:band, :].flatten(), arr[-band:, :].flatten(),
        arr[:, :band].flatten(), arr[:, -band:].flatten(),
    ])
    near_white_pct = (border_pixels > threshold).mean()
    return near_white_pct > 0.85  # >85% of border is near-white → likely unintended white edge


# ------------------------------------------------------------------
# Fonts
# ------------------------------------------------------------------

def _pdf_fonts(doc: fitz.Document) -> list[dict]:
    seen = {}
    for page in doc:
        for f in page.get_fonts(full=True):
            xref, ext, ftype, name, encoding, embedded_flag = f[:6]
            seen[name] = {"name": name, "embedded": bool(ext) or "Identity" in encoding}
    return list(seen.values())


# ------------------------------------------------------------------
# Color mode
# ------------------------------------------------------------------

def _detect_color_mode(doc: fitz.Document, page: fitz.Page) -> str:
    for img_info in page.get_images(full=True):
        xref = img_info[0]
        base = doc.extract_image(xref)
        colorspace = base.get("colorspace")
        if colorspace == 4:
            return "CMYK"
        elif colorspace == 3:
            return "RGB"
        elif colorspace == 1:
            return "Grayscale"
    return "RGB"  # default assumption if no embedded raster found (vector-only page)


# ------------------------------------------------------------------
# Color palette
# ------------------------------------------------------------------

def _extract_palette(img: Image.Image, n_colors: int = 5) -> list[dict]:
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PNG")
    buf.seek(0)
    ct = ColorThief(buf)
    palette = ct.get_palette(color_count=n_colors, quality=5)

    arr = np.array(img.convert("RGB")).reshape(-1, 3)
    total = len(arr)
    results = []
    for color in palette:
        dist = np.linalg.norm(arr - np.array(color), axis=1)
        coverage = (dist < 30).sum() / total * 100
        results.append({
            "hex": "#{:02x}{:02x}{:02x}".format(*color),
            "coverage_pct": round(float(coverage), 1),
        })
    return sorted(results, key=lambda c: -c["coverage_pct"])


# ------------------------------------------------------------------
# sRGB -> CIE Lab (D65), used for Delta-E color-distance approximation
# ------------------------------------------------------------------

def _hex_to_srgb(hexcode: str) -> tuple[float, float, float]:
    h = hexcode.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


def _srgb_to_lab(rgb: tuple[float, float, float]) -> tuple[float, float, float]:
    def _linearize(c: float) -> float:
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (_linearize(c) for c in rgb)

    # sRGB -> XYZ (D65)
    x = r * 0.4124564 + g * 0.3575761 + b * 0.1804375
    y = r * 0.2126729 + g * 0.7151522 + b * 0.0721750
    z = r * 0.0193339 + g * 0.1191920 + b * 0.9503041

    # normalize by D65 reference white
    xn, yn, zn = 0.95047, 1.0, 1.08883
    x, y, z = x / xn, y / yn, z / zn

    def _f(t: float) -> float:
        return t ** (1 / 3) if t > (6 / 29) ** 3 else (t / (3 * (6 / 29) ** 2)) + (4 / 29)

    fx, fy, fz = _f(x), _f(y), _f(z)
    L = 116 * fy - 16
    a = 500 * (fx - fy)
    bb = 200 * (fy - fz)
    return (L, a, bb)


# ------------------------------------------------------------------
# Pantone matching (open Delta-E approximation — unlicensed reference
# table in color_reference.py; swap for the licensed Pantone Connect
# API when available)
# ------------------------------------------------------------------

def match_pantone_approx(hex_color: str, reference_table: dict[str, str] | None = None) -> dict:
    """
    reference_table: {"warm red": "#C8102E", ...} — generic labels, not
    licensed Pantone codes. Returns the nearest match by approximate
    CIE76 Delta-E (Euclidean distance in Lab space).
    """
    reference_table = reference_table or REFERENCE_COLORS
    target = _srgb_to_lab(_hex_to_srgb(hex_color))

    best_label, best_dist = None, math.inf
    for label, ref_hex in reference_table.items():
        d = math.dist(target, _srgb_to_lab(_hex_to_srgb(ref_hex)))
        if d < best_dist:
            best_label, best_dist = label, d

    # Delta-E ~0 is a perfect match; >10 is generally a clearly different color.
    confidence = max(0.0, 1 - (best_dist / 30))
    return {
        "source_hex": hex_color,
        "pantone_code": None,  # None until a licensed API is wired in
        "reference_label": f"closest color reference: {best_label}",
        "delta_e": round(best_dist, 3),
        "confidence": round(confidence, 3),
    }


# ------------------------------------------------------------------
# Logo apparel-suitability checker
# ------------------------------------------------------------------

def analyze_logo(img: Image.Image, intended_method: str = "unspecified") -> dict:
    dpi = _image_dpi(img) or 72.0
    is_transparent = img.mode in ("RGBA", "LA") and img.getchannel("A").getextrema()[0] < 255
    palette = _extract_palette(img, n_colors=8)
    color_count = len(palette)

    reasons = []
    if dpi < 300:
        reasons.append(f"DPI below 300 (found {dpi})")
    if intended_method == "screen_print" and color_count > 6:
        reasons.append(f"{color_count} colors detected — screen printing favors ≤6 solid colors")
    if not is_transparent:
        reasons.append("No transparent background detected")

    if not reasons:
        verdict = "suitable"
    elif len(reasons) == 1 and "transparent" in reasons[0]:
        verdict = "needs_review"
    else:
        verdict = "unsuitable" if len(reasons) >= 2 else "needs_review"

    return {
        "is_vector": False,  # set True upstream if the original upload was SVG/AI/EPS
        "dpi_value": dpi,
        "color_count": color_count,
        "has_transparency": is_transparent,
        "verdict": verdict,
        "reasons": reasons,
    }
