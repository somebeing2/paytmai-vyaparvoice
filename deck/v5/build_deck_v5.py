#!/usr/bin/env python3
"""Build TASK 1: deck/v5/PaytmAI_VyaparVoice_pitch.pptx (9 slides, 16:9).

Hard programmatic verification gates (build fails on any violation):
- Exactly 9 slides (<= 10 max)
- Title font size >= 28 pt on every slide
- Every text run on every slide >= 18 pt
- Body word count <= 60 words on every slide
- Speaker notes between 80 and 150 words on every slide
- Zero function names, SQL terms, underscores, or campaign codes on slide surfaces
- Zero em dashes, zero en dashes, and zero emojis across slides and speaker notes
"""

from __future__ import annotations

import pathlib
import re
import sys
from typing import List, Optional, Sequence, Tuple

from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.copy_lint import find_formatting_violations  # noqa: E402

DECK_DIR = pathlib.Path(__file__).resolve().parent
SCREENS_DIR = DECK_DIR / "screens"
OUT_PPTX = DECK_DIR / "PaytmAI_VyaparVoice_pitch.pptx"

# Product blue/white palette
NAVY = RGBColor(0x00, 0x29, 0x70)
NAVY_DARK = RGBColor(0x00, 0x1B, 0x4D)
CYAN = RGBColor(0x00, 0xBA, 0xF2)
BLUE = RGBColor(0x0B, 0x5E, 0xD7)
BG_LIGHT = RGBColor(0xF4, 0xF7, 0xFB)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
BORDER = RGBColor(0xD5, 0xE0, 0xEE)
INK = RGBColor(0x10, 0x20, 0x38)
MUTED = RGBColor(0x3E, 0x50, 0x68)
TEAL = RGBColor(0x0F, 0x76, 0x6E)
TEAL_BG = RGBColor(0xE6, 0xF4, 0xF1)
AMBER = RGBColor(0x9A, 0x4A, 0x06)
AMBER_BG = RGBColor(0xFE, 0xF3, 0xC7)
RED_DARK = RGBColor(0x99, 0x1B, 0x1B)
RED_BG = RGBColor(0xFE, 0xE2, 0xE2)
BLUE_SOFT = RGBColor(0xE8, 0xF2, 0xFF)

FONT_SANS = "Calibri"
SLIDE_W = Inches(13.333)
SLIDE_H = Inches(7.5)

BANNED_SLIDE_PATTERNS = [
    r"\bCMP-[A-Z0-9-]+\b",
    r"\bOPS-[A-Z0-9-]+\b",
    r"\bPYTM-[A-Z0-9-]+\b",
    r"\bSQLite\b",
    r"\bSQL\b",
    r"\bSELECT\b",
    r"\bBEGIN IMMEDIATE\b",
    r"\bDEMO_PIN\b",
    r"[A-Za-z0-9]+_[A-Za-z0-9]+",
    r"\b[a-z_]+\.(?:py|js|db|yaml)\b",
]


def check_clean(text: str, is_slide_surface: bool = True) -> str:
    v = find_formatting_violations(text)
    if v:
        raise ValueError(f"Formatting violation {v} in text: {text!r}")
    if is_slide_surface:
        for pat in BANNED_SLIDE_PATTERNS:
            m = re.search(pat, text)
            if m:
                raise ValueError(f"Banned technical token {m.group(0)!r} on slide surface: {text!r}")
    return text


def set_bg(slide, color: RGBColor = BG_LIGHT) -> None:
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = color


def add_rect(
    slide,
    x: float,
    y: float,
    w: float,
    h: float,
    fill_color: RGBColor = WHITE,
    border_color: Optional[RGBColor] = BORDER,
    border_pt: float = 1.2,
    rounded: bool = True,
):
    st = MSO_SHAPE.ROUNDED_RECTANGLE if rounded else MSO_SHAPE.RECTANGLE
    shp = slide.shapes.add_shape(st, Inches(x), Inches(y), Inches(w), Inches(h))
    if rounded and hasattr(shp, "adjustments") and len(shp.adjustments) > 0:
        shp.adjustments[0] = 0.04
    shp.fill.solid()
    shp.fill.fore_color.rgb = fill_color
    if border_color is None:
        shp.line.fill.background()
    else:
        shp.line.color.rgb = border_color
        shp.line.width = Pt(border_pt)
    return shp


def add_text(
    slide,
    x: float,
    y: float,
    w: float,
    h: float,
    text: str,
    size: float = 18.5,
    bold: bool = False,
    color: RGBColor = INK,
    align=PP_ALIGN.LEFT,
    anchor=MSO_ANCHOR.TOP,
    line_spacing: float = 1.18,
    is_title: bool = False,
):
    assert size >= 18.0, f"Font size {size} < 18 pt minimum: {text!r}"
    if is_title:
        assert size >= 28.0, f"Title size {size} < 28 pt minimum: {text!r}"
    check_clean(text, is_slide_surface=True)
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tb.name = "SLIDE_TITLE" if is_title else "SLIDE_BODY"
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = Inches(0.05)
    tf.margin_right = Inches(0.05)
    tf.margin_top = Inches(0.03)
    tf.margin_bottom = Inches(0.03)
    tf.vertical_anchor = anchor
    for idx, ln in enumerate(text.split("\n")):
        p = tf.paragraphs[0] if idx == 0 else tf.add_paragraph()
        p.alignment = align
        p.line_spacing = line_spacing
        r = p.add_run()
        r.text = ln
        r.font.name = FONT_SANS
        r.font.size = Pt(size)
        r.font.bold = bold
        r.font.color.rgb = color
    return tb


def add_bullets(
    slide,
    x: float,
    y: float,
    w: float,
    h: float,
    items: Sequence[Tuple[str, str]],
    size: float = 18.5,
    space_after: float = 8.0,
    lead_color: RGBColor = NAVY,
    body_color: RGBColor = INK,
    line_spacing: float = 1.18,
):
    assert size >= 18.0, f"Bullet font size {size} < 18 pt minimum"
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tb.name = "SLIDE_BODY"
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = Inches(0.05)
    tf.margin_right = Inches(0.05)
    tf.margin_top = Inches(0.03)
    tf.margin_bottom = Inches(0.03)
    for idx, (lead, body) in enumerate(items):
        check_clean(lead, is_slide_surface=True)
        check_clean(body, is_slide_surface=True)
        p = tf.paragraphs[0] if idx == 0 else tf.add_paragraph()
        p.space_after = Pt(space_after)
        p.line_spacing = line_spacing
        r0 = p.add_run()
        r0.text = "* "
        r0.font.name = FONT_SANS
        r0.font.size = Pt(size)
        r0.font.bold = True
        r0.font.color.rgb = BLUE
        if lead:
            r1 = p.add_run()
            r1.text = lead + (" " if body else "")
            r1.font.name = FONT_SANS
            r1.font.size = Pt(size)
            r1.font.bold = True
            r1.font.color.rgb = lead_color
        if body:
            r2 = p.add_run()
            r2.text = body
            r2.font.name = FONT_SANS
            r2.font.size = Pt(size)
            r2.font.bold = False
            r2.font.color.rgb = body_color
    return tb


def add_arrow_right(slide, x: float, y: float, w: float = 0.28, h: float = 0.28, color: RGBColor = CYAN):
    shp = slide.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, Inches(x), Inches(y), Inches(w), Inches(h))
    shp.fill.solid()
    shp.fill.fore_color.rgb = color
    shp.line.fill.background()
    return shp


def add_fitted_image(slide, img_path: pathlib.Path, box_x: float, box_y: float, box_w: float, box_h: float):
    assert img_path.exists(), f"Missing screenshot: {img_path}"
    with Image.open(img_path) as im:
        iw, ih = im.size
    aspect = iw / float(ih)
    box_aspect = box_w / float(box_h)
    if aspect >= box_aspect:
        draw_w = box_w
        draw_h = box_w / aspect
    else:
        draw_h = box_h
        draw_w = box_h * aspect
    dx = box_x + (box_w - draw_w) / 2.0
    dy = box_y + (box_h - draw_h) / 2.0
    return slide.shapes.add_picture(str(img_path), Inches(dx), Inches(dy), width=Inches(draw_w), height=Inches(draw_h))


def add_header_and_notes(slide, title: str, notes: str) -> None:
    set_bg(slide, BG_LIGHT)
    add_rect(slide, 0, 0, 13.333, 0.10, fill_color=NAVY, border_color=None, rounded=False)
    add_rect(slide, 0, 0.10, 3.8, 0.05, fill_color=CYAN, border_color=None, rounded=False)
    add_text(slide, 0.60, 0.34, 12.13, 0.68, title, size=30.0, bold=True, color=NAVY, is_title=True)
    add_rect(slide, 0.60, 1.08, 12.13, 0.02, fill_color=BORDER, border_color=None, rounded=False)
    check_clean(notes, is_slide_surface=False)
    slide.notes_slide.notes_text_frame.text = notes


# ---------------------------------------------------------------------------
# Slide 1: Title
# ---------------------------------------------------------------------------
def build_slide_1(prs: Presentation) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(slide, NAVY_DARK)
    add_rect(slide, 0, 0, 13.333, 0.12, fill_color=CYAN, border_color=None, rounded=False)

    add_text(slide, 0.80, 1.05, 11.7, 0.95, "PaytmAI VyaparVoice", size=42.0, bold=True, color=WHITE, is_title=True)
    add_text(
        slide,
        0.80,
        2.08,
        11.4,
        0.95,
        "Voice-delivered customer win-back copilot for neighbourhood shops",
        size=24.0,
        bold=True,
        color=RGBColor(0xBA, 0xE6, 0xFD),
    )

    add_rect(slide, 0.80, 3.45, 11.73, 3.10, fill_color=RGBColor(0x05, 0x26, 0x60), border_color=RGBColor(0x1E, 0x4E, 0x9C), border_pt=1.5)
    add_bullets(
        slide,
        1.10,
        3.75,
        11.10,
        2.55,
        [
            ("Team SemiTechnical:", "Kevin Joseph | Track 1: Merchant Growth AI"),
            ("Live Demo:", "https://paytmai-vyaparvoice.onrender.com/"),
            ("GitHub:", "https://github.com/somebeing2/paytmai-vyaparvoice"),
        ],
        size=20.0,
        space_after=14.0,
        lead_color=CYAN,
        body_color=WHITE,
    )

    notes = (
        "Hi, I am Kevin Joseph from Team SemiTechnical presenting PaytmAI VyaparVoice for Track 1, Merchant Growth AI. "
        "VyaparVoice helps neighbourhood darshinis and kiranas detect silent repeat buyers from QR payment history, launch a cashback offer "
        "with a hard rupee cap, hear briefings in Kannada, Hindi, or English, and measure extra visits against an 80/20 non-offer holdout group. "
        "All store metrics in this deck come from our deterministic 60-day synthetic ledger (Sri Krishna Darshini, seed 20261025). "
        "To our knowledge the standard Paytm Soundbox is speaker-based with no microphone; this is to be validated with Paytm, so spoken replies "
        "are proposed via the Paytm for Business app and demonstrated through the browser microphone."
    )
    check_clean(notes, is_slide_surface=False)
    slide.notes_slide.notes_text_frame.text = notes


# ---------------------------------------------------------------------------
# Slide 2: Customer Loss
# ---------------------------------------------------------------------------
def build_slide_2(prs: Presentation) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    notes = (
        "Neighbourhood shops lose regulars quietly because QR payment alerts arrive as raw rupee amounts with no churn warning, and owners avoid "
        "open-ended discounts that could wipe out thin margins. Reading directly from our synthetic 60-day store ledger (240 unique buyers, 175 repeat "
        "buyers with 3 or more scans, Rs 1,74,685 30-day sales across 917 scans): CMP-WINBACK-01 detects 48 evening regulars silent for 16 to 38 days, "
        "with 40 eligible after DPDP consent and a 14-day cooldown. OPS-CARE-02 flags 2 frequent regulars unseen for 8 days possibly after a busy rush, "
        "putting Rs 4,920 of historical monthly spend at risk (2 x Rs 205 x 12 visits, not guaranteed lift). CMP-DEADHOUR-02 spots a 70 percent scan drop "
        "between 3 and 5 PM (30 and 34 scans versus 101 at 2 PM)."
    )
    add_header_and_notes(slide, "Regular Customers Slip Away Quietly", notes)

    add_rect(slide, 0.60, 1.28, 12.13, 0.62, fill_color=AMBER_BG, border_color=AMBER)
    add_text(
        slide,
        0.80,
        1.37,
        11.73,
        0.44,
        "Synthetic 60-day ledger: 175 repeat regulars of 240 buyers",
        size=19.0,
        bold=True,
        color=AMBER,
    )

    cards = [
        (
            "48 Silent Regulars",
            "Unseen 16-38 days; 40 eligible after permission and cooldown.",
            BLUE,
            BLUE_SOFT,
        ),
        (
            "Monthly Spend at Risk",
            "Rs 4,920 (2 x Rs 205 x 12), possibly after a busy rush.",
            RED_DARK,
            RED_BG,
        ),
        (
            "70% Dead-Hour Drop",
            "3-5 PM scans drop to 30 and 34 vs 101 at 2 PM.",
            NAVY,
            BLUE_SOFT,
        ),
    ]
    cx = 0.60
    cw = 3.84
    gap = 0.305
    for ctitle, cbody, fg, bg in cards:
        add_rect(slide, cx, 2.15, cw, 4.75, fill_color=WHITE, border_color=BORDER, border_pt=1.3)
        add_rect(slide, cx, 2.15, cw, 0.12, fill_color=fg, border_color=None, rounded=False)
        add_rect(slide, cx + 0.22, 2.50, cw - 0.44, 0.78, fill_color=bg, border_color=None)
        add_text(slide, cx + 0.30, 2.63, cw - 0.60, 0.52, ctitle, size=21.0, bold=True, color=fg, align=PP_ALIGN.CENTER)
        add_text(slide, cx + 0.26, 3.55, cw - 0.52, 3.00, cbody, size=19.5, color=INK, line_spacing=1.28)
        cx += cw + gap


# ---------------------------------------------------------------------------
# Slide 3: The Win-Back Copilot & Channels
# ---------------------------------------------------------------------------
def build_slide_3(prs: Presentation) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    notes = (
        "VyaparVoice runs a four-step loop: detect silent regulars from QR scan gaps, propose a policy-checked cashback pass (Rs 25 off Rs 150 or more, "
        "within the 22 percent discount limit), enforce a merchant-approved Rs 300 rupee cap with spoken 50, 80, and 100 percent alerts, and measure return "
        "visits against an 80/20 silent holdout. Voice in Kannada, Hindi, and English is the delivery layer so a shopkeeper never needs to read charts. "
        "To our knowledge the standard Paytm Soundbox is speaker-based with no microphone; this is to be validated with Paytm. Spoken briefings and alerts "
        "target the Soundbox speaker, while spoken replies and budget commands are proposed via the Paytm for Business app, with the browser microphone "
        "standing in during our live demo."
    )
    add_header_and_notes(slide, "Win-Back Copilot: Detect, Propose, Cap, Measure", notes)

    steps = [
        ("1. Detect", "Spot silent regulars", BLUE),
        ("2. Propose", "Rs 25 off Rs 150+", NAVY),
        ("3. Cap", "Hard Rs 300 stop", TEAL),
        ("4. Measure", "80/20 holdout check", AMBER),
    ]
    sx = 0.60
    sw = 2.76
    for idx, (st, sd, sc) in enumerate(steps):
        add_rect(slide, sx, 1.35, sw, 1.65, fill_color=WHITE, border_color=sc, border_pt=1.5)
        add_text(slide, sx + 0.18, 1.50, sw - 0.36, 0.50, st, size=21.0, bold=True, color=sc)
        add_text(slide, sx + 0.18, 2.08, sw - 0.36, 0.72, sd, size=18.5, color=INK)
        if idx < 3:
            add_arrow_right(slide, sx + sw + 0.04, 2.04, w=0.28, h=0.28, color=CYAN)
        sx += sw + 0.36

    # Compact Built vs Proposed channel graphic
    add_rect(slide, 0.60, 3.30, 5.90, 3.65, fill_color=WHITE, border_color=TEAL, border_pt=1.5)
    add_rect(slide, 0.60, 3.30, 5.90, 0.64, fill_color=TEAL, border_color=None, rounded=False)
    add_text(slide, 0.82, 3.40, 5.46, 0.44, "BUILT", size=19.5, bold=True, color=WHITE)
    add_bullets(
        slide,
        0.82,
        4.12,
        5.46,
        2.65,
        [
            ("Voice out:", "Briefings, cap alerts, plain readout (KN/HI/EN)."),
            ("Screens:", "Merchant, Why?, and Technical views."),
        ],
        size=18.5,
        space_after=12.0,
        lead_color=TEAL,
    )

    add_rect(slide, 6.83, 3.30, 5.90, 3.65, fill_color=WHITE, border_color=AMBER, border_pt=1.5)
    add_rect(slide, 6.83, 3.30, 5.90, 0.64, fill_color=AMBER, border_color=None, rounded=False)
    add_text(slide, 7.05, 3.40, 5.46, 0.44, "PROPOSED", size=19.5, bold=True, color=WHITE)
    add_bullets(
        slide,
        7.05,
        4.12,
        5.46,
        2.65,
        [
            ("Soundbox:", "Speaker-based, no mic (validate with Paytm)."),
            ("Paytm app:", "Voice replies (browser mic in demo)."),
        ],
        size=18.5,
        space_after=12.0,
        lead_color=AMBER,
    )


# ---------------------------------------------------------------------------
# Slide 4: Product in Action (Real Local Screenshots)
# ---------------------------------------------------------------------------
def build_slide_4(prs: Presentation) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    notes = (
        "Both screenshots on Slide 4 were captured directly from our local FastAPI application running with zero API keys set right after clicking "
        "Reset Session, using headless Chromium. On the left is the Kannada Merchant View showing the closing Soundbox briefing (111 recent QR payments), "
        "store KPIs (Rs 1,74,685 30-day sales, 240 buyers), the Draft translation badge, and the CMP-WINBACK-01 card with its Rs 300 cap. "
        "On the right is the expanded Why? provenance drawer explaining how 48 silent regulars filter to 40 eligible buyers split 32 with offer versus "
        "8 without offer, alongside the 42.2 percent cap-overrun warning suggesting a Rs 400 cap."
    )
    add_header_and_notes(slide, "Product in Action (Local App, Zero Keys)", notes)

    # Left screenshot card
    add_rect(slide, 0.60, 1.30, 5.92, 5.72, fill_color=WHITE, border_color=BORDER, border_pt=1.3)
    add_text(slide, 0.80, 1.42, 5.52, 0.50, "Kannada Merchant View & Win-Back Card", size=19.0, bold=True, color=NAVY)
    add_fitted_image(slide, SCREENS_DIR / "merchant_view_kn.png", 0.74, 1.98, 5.64, 4.90)

    # Right screenshot card
    add_rect(slide, 6.81, 1.30, 5.92, 5.72, fill_color=WHITE, border_color=BORDER, border_pt=1.3)
    add_text(slide, 7.01, 1.42, 5.52, 0.50, "Expanded Why? Provenance Panel", size=19.0, bold=True, color=NAVY)
    add_fitted_image(slide, SCREENS_DIR / "why_panel.png", 6.95, 1.98, 5.64, 4.90)


# ---------------------------------------------------------------------------
# Slide 5: Measurement & Simulated 48h Outcome
# ---------------------------------------------------------------------------
def build_slide_5(prs: Presentation) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    notes = (
        "Slide 5 shows how we separate real extra visits from regulars who would have walked in anyway, followed by the canonical 48-hour simulation "
        "in simulate_campaign_48h. Out of 40 eligible regulars, 32 get the Rs 25 pass (capped at Rs 300, 12 bills) and 8 get no offer. In our canonical "
        "synthetic simulation, 12 of 32 (37.5 percent) return versus 1 of 8 (12.5 percent) in holdout. Subtracting 4 expected organic visits leaves "
        "8 extra visits worth Rs 1,740. At an assumed 30 percent margin, profit is +Rs 222 before fee and +Rs 91.50 after an assumed 5 percent promo fee "
        "on Rs 2,610 redeemed bills (Explain Simply rounds post-fee profit to about Rs 92). Single-wave Fisher p is 0.2364 and Bayesian P(post-fee > 0) "
        "is 52.1 percent, so one wave is directional only; pooling 50 shops (n = 2,000) reaches 92.5 percent power at +7 percentage points."
    )
    add_header_and_notes(slide, "Holdout Design and Simulated 48h Outcome", notes)

    add_rect(slide, 0.60, 1.26, 12.13, 0.62, fill_color=AMBER_BG, border_color=AMBER, border_pt=1.4)
    add_text(
        slide,
        0.80,
        1.35,
        11.73,
        0.44,
        "Illustrative simulation on synthetic data, not evidence of lift",
        size=19.5,
        bold=True,
        color=AMBER,
        align=PP_ALIGN.CENTER,
    )

    # Left: Cap, Holdout & Grades A/B/C
    add_rect(slide, 0.60, 2.08, 5.85, 4.92, fill_color=WHITE, border_color=BORDER, border_pt=1.3)
    add_bullets(
        slide,
        0.82,
        2.28,
        5.42,
        4.52,
        [
            ("Design:", "Rs 300 cap; 80/20 holdout (32 vs 8)."),
            ("Grade A:", "Observed ledger counts."),
            ("Grade B:", "Offer vs holdout returns."),
            ("Grade C:", "Assumed margin and fee profit."),
        ],
        size=19.0,
        space_after=16.0,
        lead_color=NAVY,
    )

    # Right: Simulated 48h results (showing Rs 91.50, zero p-value/power/Bayesian/Rs 92 aside)
    add_rect(slide, 6.73, 2.08, 6.00, 4.92, fill_color=WHITE, border_color=BLUE, border_pt=1.5)
    add_bullets(
        slide,
        6.95,
        2.28,
        5.56,
        4.52,
        [
            ("Returns:", "12/32 (37.5%) vs 1/8 (12.5%)."),
            ("Extra visits:", "8 visits (Rs 1,740 sales)."),
            ("Pre-fee:", "+Rs 222 (assumed 30% margin)."),
            ("Post-5%-fee:", "+Rs 91.50 (assumed fee)."),
        ],
        size=19.0,
        space_after=16.0,
        lead_color=BLUE,
    )


# ---------------------------------------------------------------------------
# Slide 6: Why the Numbers Can Be Trusted
# ---------------------------------------------------------------------------
def build_slide_6(prs: Presentation) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    notes = (
        "Every rupee figure, count, and confidence interval is computed deterministically in Python from SQLite; external models never calculate math "
        "and assert_zero_pii strips customer names, IDs, phones, and UPI handles before any outbound call. ProviderRouter tries Sarvam AI first "
        "(bulbul:v3, saaras:v4, sarvam-105b-conversations), fails over silently to Groq (openai/gpt-oss-20b, whisper-large-v3-turbo, orpheus-v1-english), "
        "and falls back to browser Web Speech plus deterministic templates. Before any AI sentence is shown, verify_numeric_grounding checks ASCII, "
        "Devanagari, and Kannada digits against store facts. An immutable audit_logs table records approvals and alerts, while persistent SQLite caching, "
        "call caps (60 global, 35 session), IP rate limits, and DEMO_PIN gating protect credits on Render. Repo preflight runs 12 gates, 7 test suites "
        "(311 asserts), and a 21-check QA battery."
    )
    add_header_and_notes(slide, "Why Every Number Can Be Trusted", notes)

    boxes = [
        ("1. Code Math", "Python computes figures; zero PII leaves.", NAVY, BLUE_SOFT),
        ("2. Fallback", "Sarvam -> Groq -> Browser speech & templates.", BLUE, BLUE_SOFT),
        ("3. Digit Gate", "Verifies EN, HI, KN digits on AI replies.", TEAL, TEAL_BG),
        ("4. Safeguards", "Audit log, cache, call caps, PIN gate.", AMBER, AMBER_BG),
    ]
    bx = 0.60
    bw = 2.76
    for idx, (bt, bd, bc, bbg) in enumerate(boxes):
        add_rect(slide, bx, 1.45, bw, 3.85, fill_color=WHITE, border_color=bc, border_pt=1.5)
        add_rect(slide, bx, 1.45, bw, 0.72, fill_color=bbg, border_color=None, rounded=False)
        add_text(slide, bx + 0.16, 1.58, bw - 0.32, 0.48, bt, size=19.5, bold=True, color=bc)
        add_text(slide, bx + 0.18, 2.40, bw - 0.36, 2.65, bd, size=18.5, color=INK, line_spacing=1.25)
        if idx < 3:
            add_arrow_right(slide, bx + bw + 0.04, 3.22, w=0.28, h=0.28, color=CYAN)
        bx += bw + 0.36

    add_rect(slide, 0.60, 5.65, 12.13, 1.25, fill_color=NAVY, border_color=None)
    add_text(
        slide,
        0.85,
        5.92,
        11.63,
        0.72,
        "Repo verification: 12 preflight gates, 7 test suites (311 asserts), 21 QA checks.",
        size=20.0,
        bold=True,
        color=WHITE,
        align=PP_ALIGN.CENTER,
    )


# ---------------------------------------------------------------------------
# Slide 7: Business Case & Margin Limitation
# ---------------------------------------------------------------------------
def build_slide_7(prs: Presentation) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    notes = (
        "Slide 7 outlines a qualitative business case with zero invented market sizes or adoption numbers. Merchants get capped, holdout-measured "
        "win-back in Kannada, Hindi, or English. For Paytm (assumption, to verify with Paytm), this could deepen engagement on existing Soundbox and "
        "QR surfaces with measurable offers. Who pays remains an open assumption; our waterfall models a 5 percent promo fee on redeemed bills solely "
        "as an assumption. Our unit economics script models per-merchant delivery at Rs 48 per month cached (Rs 71.80 uncached, modelled assumption "
        "including Rs 43 modelled messaging not sent by this demo). Crucially, a Rs 25 pass breaks even post-fee at 24.7 percent margin: it suits "
        "30 percent margin darshinis (+Rs 91.50) first, whereas 15 to 20 percent margin kiranas (-Rs 82.50 at 20 percent) need smaller category presets."
    )
    add_header_and_notes(slide, "Business Case and Store Margin Limits", notes)

    quad = [
        ("For Merchants", "Capped, measured win-back in Kannada, Hindi, or English.", BLUE),
        ("For Paytm (Assumption)", "More use of Soundbox and QR with measurable offers.", TEAL),
        ("Who Pays & Modelled Cost", "Open assumption (5% fee assumed); Rs 48/mo cached cost (modelled assumption).", NAVY),
        ("Margin Limitation", "Positive near 30% margin (darshinis first); kiranas need smaller presets.", AMBER),
    ]
    coords = [(0.60, 1.38), (6.78, 1.38), (0.60, 4.25), (6.78, 4.25)]
    for (qx, qy), (qt, qd, qc) in zip(coords, quad):
        add_rect(slide, qx, qy, 5.95, 2.60, fill_color=WHITE, border_color=BORDER, border_pt=1.3)
        add_rect(slide, qx, qy, 0.14, 2.60, fill_color=qc, border_color=None, rounded=False)
        add_text(slide, qx + 0.34, qy + 0.22, 5.40, 0.52, qt, size=21.0, bold=True, color=qc)
        add_text(slide, qx + 0.34, qy + 0.88, 5.40, 1.50, qd, size=19.0, color=INK, line_spacing=1.25)


# ---------------------------------------------------------------------------
# Slide 8: Pilot Plan & Honest Limitations
# ---------------------------------------------------------------------------
def build_slide_8(prs: Presentation) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    notes = (
        "To test whether real customers respond, we propose an opt-in multi-shop darshini pilot (sized at 50 shops, 2,000 eligible buyers, 1,600 offer "
        "versus 400 holdout for 92.5 percent power at +7 percentage points) governed by strict stop rules: halt if pooled post-fee profit is negative, "
        "if any cap overruns, or if opt-outs spike. Right-hand limitations are stated plainly: all 60-day store transactions and 48-hour returns are "
        "synthetic; Hindi and Kannada copy are drafts awaiting native speaker review; to our knowledge the standard Paytm Soundbox is speaker-based "
        "with no microphone, which is to be validated with Paytm alongside Paytm for Business voice input; and any single 40-buyer wave is directional only."
    )
    add_header_and_notes(slide, "Proposed Pilot Plan and Honest Limits", notes)

    # Left: Proposed Pilot
    add_rect(slide, 0.60, 1.38, 5.85, 5.55, fill_color=WHITE, border_color=TEAL, border_pt=1.5)
    add_rect(slide, 0.60, 1.38, 5.85, 0.68, fill_color=TEAL, border_color=None, rounded=False)
    add_text(slide, 0.84, 1.49, 5.36, 0.46, "PROPOSED OPT-IN PILOT", size=20.0, bold=True, color=WHITE)
    add_bullets(
        slide,
        0.84,
        2.32,
        5.36,
        4.30,
        [
            ("Design:", "Multi-shop darshini pilot with randomized 80/20 holdout."),
            ("Stop rules:", "Halt on negative post-fee return, cap overrun, or opt-outs."),
        ],
        size=19.5,
        space_after=20.0,
        lead_color=TEAL,
    )

    # Right: Honest Limitations
    add_rect(slide, 6.78, 1.38, 5.95, 5.55, fill_color=WHITE, border_color=AMBER, border_pt=1.5)
    add_rect(slide, 6.78, 1.38, 5.95, 0.68, fill_color=AMBER, border_color=None, rounded=False)
    add_text(slide, 7.02, 1.49, 5.46, 0.46, "HONEST LIMITATIONS", size=20.0, bold=True, color=WHITE)
    add_bullets(
        slide,
        7.02,
        2.28,
        5.46,
        4.45,
        [
            ("Data:", "Synthetic 60-day ledger and simulated returns."),
            ("Language:", "Draft Hindi and Kannada pending native review."),
            ("Hardware:", "Speaker-based Soundbox, no mic (validate with Paytm)."),
            ("Sample:", "Single-wave results are directional only."),
        ],
        size=18.5,
        space_after=12.0,
        lead_color=AMBER,
    )


# ---------------------------------------------------------------------------
# Slide 9: AI Tools & Team
# ---------------------------------------------------------------------------
def build_slide_9(prs: Presentation) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    notes = (
        "Slide 9 summarizes our AI tools note (docs/AI_TOOLS_NOTE.pdf) and team attribution. During development, Claude (by Anthropic) was used in chat "
        "for planning, drafting prompts, and reviewing outputs, paired with an AI coding agent for implementation (exact coding-agent model to be confirmed "
        "by the team). At runtime, Sarvam AI (bulbul:v3, saaras:v4, sarvam-105b-conversations) is primary, Groq (openai/gpt-oss-20b, whisper-large-v3-turbo, "
        "orpheus-v1-english) is secondary, and browser Web Speech with deterministic templates is tertiary. Kevin Joseph defined the customer-loss "
        "framing, hard rupee caps, holdout evaluation, and disclosures, verified in the repository by 12 preflight gates, 7 test suites, and secret "
        "scans (manual testing by the team to be confirmed by the team)."
    )
    add_header_and_notes(slide, "AI Tools, Safeguards, and Team", notes)

    add_rect(slide, 0.60, 1.38, 6.35, 5.55, fill_color=WHITE, border_color=BORDER, border_pt=1.3)
    add_bullets(
        slide,
        0.84,
        1.68,
        5.88,
        5.00,
        [
            ("Build tools:", "Claude for planning/review; AI coding agent for code."),
            ("Runtime AI:", "Sarvam primary, Groq backup, browser speech fallback."),
            ("Human role:", "Problem, caps, holdout rules, disclosures, 12-gate checks."),
        ],
        size=19.0,
        space_after=20.0,
        lead_color=NAVY,
    )

    add_rect(slide, 7.23, 1.38, 5.50, 5.55, fill_color=NAVY, border_color=None)
    add_text(slide, 7.50, 1.72, 4.96, 0.55, "Team SemiTechnical", size=24.0, bold=True, color=CYAN)
    add_text(slide, 7.50, 2.38, 4.96, 0.55, "Kevin Joseph", size=22.0, bold=True, color=WHITE)
    add_text(slide, 7.50, 3.30, 4.96, 0.44, "Live Demo:", size=18.5, bold=True, color=CYAN)
    add_text(slide, 7.50, 3.74, 4.96, 0.50, "paytmai-vyaparvoice.onrender.com", size=18.0, color=WHITE)
    add_text(slide, 7.50, 4.55, 4.96, 0.44, "GitHub Repository:", size=18.5, bold=True, color=CYAN)
    add_text(slide, 7.50, 4.99, 4.96, 0.50, "github.com/somebeing2/paytmai-vyaparvoice", size=18.0, color=WHITE)


# ---------------------------------------------------------------------------
# Strict Verification Audit
# ---------------------------------------------------------------------------
def verify_deck(pptx_path: pathlib.Path) -> None:
    prs = Presentation(str(pptx_path))
    n_slides = len(prs.slides)
    assert n_slides == 9, f"Expected 9 slides, got {n_slides}"
    print(f"=== Verifying {pptx_path.name} ({n_slides} slides) ===")
    for idx, sl in enumerate(prs.slides, start=1):
        title_min = None
        body_min = None
        all_min = None
        body_words = 0
        total_words = 0

        for shp in sl.shapes:
            # Bounds check
            left_in = shp.left / 914400.0
            top_in = shp.top / 914400.0
            right_in = (shp.left + shp.width) / 914400.0
            bot_in = (shp.top + shp.height) / 914400.0
            assert left_in >= -0.02 and top_in >= -0.02, f"Slide {idx} shape out of top/left bounds"
            assert right_in <= 13.36 and bot_in <= 7.52, f"Slide {idx} shape overflows slide: right={right_in:.2f}, bot={bot_in:.2f}"

            if not shp.has_text_frame:
                continue
            txt = shp.text_frame.text.strip()
            if not txt:
                continue
            check_clean(txt, is_slide_surface=True)
            wc = len([w for w in txt.split() if w != "*"])
            total_words += wc
            is_title = (shp.name == "SLIDE_TITLE")
            if not is_title:
                body_words += wc

            for p in shp.text_frame.paragraphs:
                for r in p.runs:
                    if not r.text.strip():
                        continue
                    pt = r.font.size.pt if r.font.size else 0.0
                    all_min = pt if all_min is None else min(all_min, pt)
                    if is_title:
                        title_min = pt if title_min is None else min(title_min, pt)
                    else:
                        body_min = pt if body_min is None else min(body_min, pt)

        notes_txt = sl.notes_slide.notes_text_frame.text.strip() if sl.has_notes_slide else ""
        check_clean(notes_txt, is_slide_surface=False)
        notes_wc = len(notes_txt.split())

        assert title_min is not None and title_min >= 28.0, f"Slide {idx} title font {title_min} < 28 pt"
        assert body_min is not None and body_min >= 18.0, f"Slide {idx} body font {body_min} < 18 pt"
        assert body_words <= 60, f"Slide {idx} body words {body_words} > 60 limit"
        assert 80 <= notes_wc <= 150, f"Slide {idx} speaker notes words {notes_wc} outside [80, 150]"

        print(
            f"  Slide {idx}: body_words={body_words:2d} (<=60) | total_words={total_words:2d} | "
            f"title_min={title_min:.1f}pt (>=28) | body_min={body_min:.1f}pt (>=18) | notes_words={notes_wc:3d} (80..150)"
        )


def main() -> None:
    prs = Presentation()
    prs.slide_width = SLIDE_W
    prs.slide_height = SLIDE_H

    build_slide_1(prs)
    build_slide_2(prs)
    build_slide_3(prs)
    build_slide_4(prs)
    build_slide_5(prs)
    build_slide_6(prs)
    build_slide_7(prs)
    build_slide_8(prs)
    build_slide_9(prs)

    OUT_PPTX.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(OUT_PPTX))
    verify_deck(OUT_PPTX)


if __name__ == "__main__":
    main()
