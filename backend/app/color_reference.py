"""
Open, unlicensed color reference table used for "closest color reference"
matching (see match_pantone_approx in analysis_pipeline.py).

IMPORTANT: these are generic descriptive labels, not licensed Pantone(R)
codes or values. Never render these as "Pantone" anywhere in the UI or PDF
report — see the Non-negotiable Behaviors section of the build brief.
Swap this table (and match_pantone_approx) for a licensed Pantone Connect
API integration when one is available.
"""

REFERENCE_COLORS: dict[str, str] = {
    "warm red": "#C8102E",
    "true red": "#BF0A30",
    "brick red": "#9E3039",
    "deep maroon": "#5B1A18",
    "burnt orange": "#C1440E",
    "tangerine": "#F28C28",
    "golden yellow": "#F5C518",
    "mustard": "#C9A227",
    "lemon": "#F7EA48",
    "olive": "#5A6E3C",
    "moss green": "#4A5D23",
    "forest green": "#0B6623",
    "kelly green": "#4CBB17",
    "mint": "#98FF98",
    "teal": "#008080",
    "deep teal": "#014D4E",
    "sky blue": "#87CEEB",
    "cornflower blue": "#6495ED",
    "royal blue": "#4169E1",
    "navy": "#1B2A4A",
    "cobalt": "#0047AB",
    "periwinkle": "#8E9DE3",
    "violet": "#7F3FBF",
    "plum": "#673147",
    "magenta": "#D6006D",
    "hot pink": "#FF3399",
    "blush pink": "#F4C2C2",
    "coral": "#FF7F50",
    "salmon": "#FA8072",
    "tan": "#D2B48C",
    "khaki": "#C3B091",
    "sand": "#E8DCC5",
    "charcoal": "#333333",
    "slate gray": "#708090",
    "cool gray": "#8C92AC",
    "silver": "#C0C0C0",
    "ivory": "#FFFFF0",
    "off white": "#F7F5F0",
    "jet black": "#0A0A0A",
    "chocolate brown": "#5C3A21",
}
