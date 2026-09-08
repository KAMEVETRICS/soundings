"""Rebuild the RYO-CHAN Project Submission Form for Soundings.

The Discord blank is not reachable from this machine. The copy floating on
GitHub is another team's filled PDF (not fillable). This script redraws the
same A4 layout with Soundings answers.

Edit EMAIL and DEMO_VIDEO below, then:

    python scripts/fill_submission_form.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parent.parent
FORM_DIR = Path(__file__).resolve().parent / "form"
BANNER_SRC = FORM_DIR / "banner.png"
BANNER_CROP = FORM_DIR / "banner_crop.png"
OUTPUT = ROOT / "RYOCHAN-Project-Submission-Form.pdf"

# Fill these before the Discord /apply step.
EMAIL = "kcfreshkl@gmail.com"
DEMO_VIDEO = ""  # Drive / Dropbox / OneDrive share URL
DEMO_VIDEO_PASSWORD = ""  # only if the file is locked

NAME = "kongclaves"
ROLE = "Solo builder"
ORGANIZER_REPO = "https://github.com/RYO-Digital/ryochan-hackathon_repository-142"
GITHUB = ORGANIZER_REPO

BLACK = colors.black
LABEL_W = 92
MARGIN = 18 * mm


def _email() -> str:
    return EMAIL.strip()


def _demo_video() -> str:
    link = DEMO_VIDEO.strip()
    if not link:
        return ""
    if DEMO_VIDEO_PASSWORD.strip():
        return f"{link}  (password: {DEMO_VIDEO_PASSWORD.strip()})"
    return link


def _styles() -> dict[str, ParagraphStyle]:
    return {
        "h1": ParagraphStyle(
            "h1",
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=16,
            spaceBefore=10,
            spaceAfter=6,
            textColor=BLACK,
        ),
        "label": ParagraphStyle(
            "label",
            fontName="Helvetica-Bold",
            fontSize=8.5,
            leading=11,
            textColor=BLACK,
        ),
        "body": ParagraphStyle(
            "body",
            fontName="Helvetica",
            fontSize=8.5,
            leading=11,
            textColor=BLACK,
            alignment=TA_LEFT,
        ),
        "th": ParagraphStyle(
            "th",
            fontName="Helvetica-Bold",
            fontSize=8.5,
            leading=11,
            alignment=TA_CENTER,
            textColor=BLACK,
        ),
        "td": ParagraphStyle(
            "td",
            fontName="Helvetica",
            fontSize=8.5,
            leading=11,
            alignment=TA_CENTER,
            textColor=BLACK,
        ),
        "td_left": ParagraphStyle(
            "td_left",
            fontName="Helvetica",
            fontSize=8.5,
            leading=11,
            alignment=TA_LEFT,
            textColor=BLACK,
        ),
    }


def _p(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(text.replace("\n", "<br/>"), style)


def _kv_table(rows: list[tuple[str, str]], styles: dict[str, ParagraphStyle], width: float) -> Table:
    data = []
    for label, value in rows:
        data.append(
            [
                _p(label, styles["label"]),
                _p(value, styles["body"]),
            ]
        )
    table = Table(data, colWidths=[LABEL_W, width - LABEL_W], repeatRows=0)
    table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.6, BLACK),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def _members_block(styles: dict[str, ParagraphStyle], width: float) -> Table:
    inner_w = width - LABEL_W
    col = inner_w / 3
    inner = Table(
        [
            [_p("Name", styles["th"]), _p("Role", styles["th"]), _p("Email", styles["th"])],
            [_p(NAME, styles["td"]), _p(ROLE, styles["td"]), _p(_email(), styles["td"])],
            ["", "", ""],
            ["", "", ""],
            ["", "", ""],
            ["", "", ""],
        ],
        colWidths=[col, col, col],
        rowHeights=[16, 16, 16, 16, 16, 16],
    )
    inner.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.6, BLACK),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    outer = Table(
        [
            [_p("Total Members", styles["label"]), _p("1", styles["body"])],
            [_p("Members", styles["label"]), inner],
        ],
        colWidths=[LABEL_W, inner_w],
    )
    outer.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.6, BLACK),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (0, -1), 6),
                ("RIGHTPADDING", (0, 0), (0, -1), 6),
                ("LEFTPADDING", (1, 0), (1, 0), 6),
                ("RIGHTPADDING", (1, 0), (1, 0), 6),
                ("LEFTPADDING", (1, 1), (1, 1), 0),
                ("RIGHTPADDING", (1, 1), (1, 1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (1, 1), (1, 1), 0),
                ("BOTTOMPADDING", (1, 1), (1, 1), 0),
            ]
        )
    )
    return outer


def _crop_banner() -> Path:
    src = PILImage.open(BANNER_SRC)
    w, h = src.size
    # Official form crops the lower floor / legal line off the hero art.
    crop_h = int(h * 0.62)
    src.crop((0, 0, w, crop_h)).save(BANNER_CROP)
    return BANNER_CROP


def _banner(width: float) -> Image:
    path = _crop_banner()
    with PILImage.open(path) as im:
        iw, ih = im.size
    height = width * ih / iw
    return Image(str(path), width=width, height=height)


def _page_number(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 9)
    canvas.drawRightString(A4[0] - MARGIN, 12 * mm, str(doc.page))
    canvas.restoreState()


def build() -> Path:
    styles = _styles()
    width = A4[0] - 2 * MARGIN
    story: list = []

    story.append(_banner(width))
    story.append(Spacer(1, 10))
    story.append(_members_block(styles, width))
    story.append(Spacer(1, 12))
    story.append(_p("Overview", styles["h1"]))
    story.append(
        _kv_table(
            [
                ("Project", "Soundings"),
                ("Track", "Track 2 (Dashboards &amp; Interfaces)"),
                (
                    "Problem",
                    "Fear &amp; Greed can disagree with BTC funding. RYO does not publish "
                    "wallets or open interest, so those prints cannot be shown.",
                ),
                (
                    "Solution",
                    "Read-only terminal on RYO's six research tools. Analytics reports "
                    "crowd vs tape as S = 0.5 Fear &amp; Greed + 0.5 BTC funding percentile. "
                    "Missing fields stay blank.",
                ),
                (
                    "Key Features",
                    "Overview, Analytics (S and gap), Screener, Token, Sentiment, Compare, "
                    "Claw, JSON /api.",
                ),
                (
                    "Target Users",
                    "Traders who want a 30-second crowd-vs-tape read.",
                ),
                (
                    "Scope",
                    "Live RYO MCP: market_overview, scan_market, analyze_token, "
                    "deep_analysis, compare_tokens, monitor_market_sentiment_shift. "
                    "Optional TrueNorth F&amp;G / MVRV. No orders.",
                ),
                (
                    "Limitations",
                    "No wallet lookup, no open interest. Runs locally on port 8001.",
                ),
            ],
            styles,
            width,
        )
    )

    story.append(PageBreak())
    story.append(_p("Tech Stack", styles["h1"]))
    story.append(
        _kv_table(
            [
                ("Frontend Stack", "Jinja2, CSS, vanilla JS"),
                ("Backend Stack", "Python 3.12, FastAPI, uvicorn, httpx"),
                (
                    "AI Model(s)",
                    "None on market desks. Claw optional: OpenRouter x-ai/grok-4.3",
                ),
                (
                    "Other Technologies",
                    "python-dotenv; optional TrueNorth MCP",
                ),
            ],
            styles,
            width,
        )
    )
    story.append(Spacer(1, 12))
    story.append(_p("Repository / Demo", styles["h1"]))
    story.append(
        _kv_table(
            [
                ("Github Repository", GITHUB),
                ("Demo Video", _demo_video()),
                ("Documentation", "README.md"),
            ],
            styles,
            width,
        )
    )
    story.append(Spacer(1, 12))
    story.append(_p("Testing Information", styles["h1"]))
    story.append(
        _kv_table(
            [
                (
                    "How to run the Project",
                    "http://127.0.0.1:8001/analytics",
                ),
                ("Prerequisites", "Python 3.12, pip, RYO_MCP_KEY"),
                (
                    "Installation Steps",
                    "Clone; python -m venv .venv; pip install -r requirements.txt; "
                    "copy .env.example to .env",
                ),
                (
                    "Environment Variables",
                    "RYO_MCP_URL, RYO_MCP_KEY. Optional: OPENROUTER_API_KEY, "
                    "TRUENORTH_MCP_URL, TRUENORTH_MCP_TOKEN",
                ),
                ("Build Command", "None"),
                (
                    "Run Command",
                    "uvicorn app.main:app --host 127.0.0.1 --port 8001",
                ),
                ("Test Command", "python scripts/probe_endpoints.py"),
                ("Test Account(s)", "None"),
            ],
            styles,
            width,
        )
    )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=14 * mm,
        bottomMargin=16 * mm,
        title="RYO-CHAN Project Submission Form - Soundings",
        author=NAME,
    )
    doc.build(story, onFirstPage=_page_number, onLaterPages=_page_number)
    return OUTPUT


if __name__ == "__main__":
    path = build()
    print(f"Wrote {path}")
