import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

OUT_DIR = "/home/user"
ASSET_DIR = "/home/user/scripts/deck_assets"
os.makedirs(ASSET_DIR, exist_ok=True)

PPTX_PATH = os.path.join(OUT_DIR, "PaytmAI_VyaparVoice_SemiTechnical.pptx")

# Brand & Palette
NAVY_DARK = RGBColor(0x00, 0x1B, 0x4D)   # #001B4D Deep Paytm Hero Navy
NAVY      = RGBColor(0x00, 0x29, 0x70)   # #002970 Paytm Navy
CYAN      = RGBColor(0x00, 0xBA, 0xF2)   # #00BAF2 Paytm Cyan
CYAN_DARK = RGBColor(0x02, 0x84, 0xC7)   # #0284C7 Accessible Cyan-Blue
CYAN_SOFT = RGBColor(0xE0, 0xF7, 0xFE)   # #E0F7FE Soft Cyan Tint
BG_LIGHT  = RGBColor(0xF5, 0xF8, 0xFC)   # #F5F8FC Slide Canvas
WHITE     = RGBColor(0xFF, 0xFF, 0xFF)
INK       = RGBColor(0x0F, 0x17, 0x2A)   # #0F172A Primary Text
MUTED     = RGBColor(0x47, 0x55, 0x69)   # #475569 Secondary Text
BORDER    = RGBColor(0xD8, 0xE3, 0xF0)   # #D8E3F0 Subtle Card Border
EMERALD   = RGBColor(0x05, 0x96, 0x69)   # #059669 Positive Lift Green
EMER_SOFT = RGBColor(0xEC, 0xFD, 0xF5)   # #ECFDF5 Soft Mint
AMBER     = RGBColor(0xD9, 0x77, 0x06)   # #D97706 Alert Amber
AMB_SOFT  = RGBColor(0xFF, 0xFB, 0xEB)   # #FFFBEB Soft Amber
INDIGO_SF = RGBColor(0xEE, 0xF2, 0xFF)   # #EEF2FF Soft Indigo

FONT_MAIN = "Liberation Sans"


def generate_charts():
    plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Liberation Sans", "Arial"]
    plt.rcParams["axes.edgecolor"] = "#CBD5E1"
    plt.rcParams["axes.linewidth"] = 0.8

    # 1. Chart 1: Hourly Store UPI Scans showing 3-5 PM Dead-Hour Trough
    hours = ["7A", "8A", "9A", "10A", "11A", "12P", "1P", "2P", "3P", "4P", "5P", "6P", "7P", "8P", "9P"]
    scans = [52, 86, 94, 64, 38, 78, 92, 68, 22, 19, 54, 82, 96, 88, 58]
    colors = ["#F59E0B" if h in ("3P", "4P") else "#002970" for h in hours]

    fig, ax = plt.subplots(figsize=(5.6, 2.75), dpi=260)
    fig.patch.set_facecolor("#FFFFFF")
    ax.set_facecolor("#FFFFFF")
    bars = ax.bar(hours, scans, color=colors, width=0.64, zorder=3)
    ax.grid(axis="y", linestyle="--", alpha=0.45, color="#CBD5E1", zorder=0)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.set_ylabel("Avg UPI Scans / Hr", fontsize=9.5, fontweight="bold", color="#334155")
    ax.set_title("Typical Merchant Hourly UPI Footfall (Dead-Hour Dip Highlighted)", fontsize=10.5, fontweight="bold", color="#002970", pad=10)
    ax.tick_params(axis="both", labelsize=8.2, colors="#475569")
    ax.set_ylim(0, 115)

    # Annotate Dead-Hour Trough
    ax.annotate(
        "3–5 PM Dead-Hour\n(-68% vs Peak)",
        xy=(8.5, 23),
        xytext=(6.6, 86),
        arrowprops=dict(arrowstyle="->", color="#D97706", lw=1.6),
        fontsize=8.5,
        fontweight="bold",
        color="#B45309",
        bbox=dict(boxstyle="round,pad=0.3", fc="#FFFBEB", ec="#F59E0B", lw=1),
    )
    plt.tight_layout()
    chart1_path = os.path.join(ASSET_DIR, "chart_hourly_trough.png")
    plt.savefig(chart1_path, dpi=260)
    plt.close(fig)

    # 2. Chart 2: Causal Holdout Attribution Proof (Slide 7)
    fig, ax = plt.subplots(figsize=(5.3, 2.85), dpi=260)
    fig.patch.set_facecolor("#FFFFFF")
    ax.set_facecolor("#FFFFFF")
    groups = ["Silent Control Group\n(20% Holdout · No Offer)", "VyaparVoice Cohort\n(80% Nudged · ₹25 UPI Pass)"]
    rates = [12.5, 37.5]
    bar_cols = ["#94A3B8", "#059669"]
    b2 = ax.bar(groups, rates, color=bar_cols, width=0.46, zorder=3)
    ax.grid(axis="y", linestyle="--", alpha=0.45, color="#CBD5E1", zorder=0)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.set_ylabel("48-Hour Store Return Rate (%)", fontsize=9.5, fontweight="bold", color="#334155")
    ax.set_title("Causal 80/20 Holdout Proof (MVP Simulation)", fontsize=10.5, fontweight="bold", color="#002970", pad=10)
    ax.set_ylim(0, 48)
    ax.tick_params(axis="both", labelsize=8.8, colors="#334155")
    for rect, val in zip(b2, rates):
        ax.text(
            rect.get_x() + rect.get_width() / 2,
            val + 1.5,
            f"{val:.1f}%",
            ha="center",
            va="bottom",
            fontsize=10.5,
            fontweight="bold",
            color="#0F172A",
        )
    ax.annotate(
        "3.0x True Return Lift\n+₹1,740 Net Sales (5.8x ROI)",
        xy=(1, 37.5),
        xytext=(0.05, 36.5),
        arrowprops=dict(arrowstyle="->", color="#059669", lw=1.6),
        fontsize=8.5,
        fontweight="bold",
        color="#065F46",
        bbox=dict(boxstyle="round,pad=0.35", fc="#ECFDF5", ec="#10B981", lw=1),
    )
    plt.tight_layout()
    chart2_path = os.path.join(ASSET_DIR, "chart_holdout_lift.png")
    plt.savefig(chart2_path, dpi=260)
    plt.close(fig)

    # 3. Chart 3: ARR Scaling Across 1.57 Cr Paytm Device Merchants (Slide 8)
    fig, ax = plt.subplots(figsize=(5.5, 3.0), dpi=260)
    fig.patch.set_facecolor("#FFFFFF")
    ax.set_facecolor("#FFFFFF")
    tiers = ["1% Adoption\n(1.57L Shops)", "5% Base Case\n(7.85L Shops)", "10% Scale\n(15.7L Shops)"]
    saas_arr = np.array([14.9, 74.4, 148.8])       # ₹79/mo * 12
    perf_arr = np.array([19.2, 96.0, 192.0])       # Campaign success take-rate
    credit_arr = np.array([14.5, 72.6, 145.2])     # Working-capital lead origination uplift

    x = np.arange(len(tiers))
    w = 0.48
    ax.bar(x, saas_arr, width=w, label="₹79/mo Pro Add-on", color="#002970", zorder=3)
    ax.bar(x, perf_arr, width=w, bottom=saas_arr, label="5% Promo Redemption Fee", color="#00BAF2", zorder=3)
    ax.bar(x, credit_arr, width=w, bottom=saas_arr + perf_arr, label="Merchant Credit Origination", color="#10B981", zorder=3)

    totals = saas_arr + perf_arr + credit_arr
    for xi, tot in zip(x, totals):
        ax.text(xi, tot + 10, f"₹{int(round(tot))} Cr", ha="center", va="bottom", fontsize=10, fontweight="bold", color="#001B4D")

    ax.set_xticks(x)
    ax.set_xticklabels(tiers, fontsize=8.8, fontweight="bold", color="#334155")
    ax.set_ylabel("Annualized Revenue (₹ Crore)", fontsize=9.5, fontweight="bold", color="#334155")
    ax.set_title("Paytm Ecosystem Monetization Potential (₹ Cr ARR)", fontsize=10.5, fontweight="bold", color="#002970", pad=10)
    ax.set_ylim(0, 560)
    ax.grid(axis="y", linestyle="--", alpha=0.45, color="#CBD5E1", zorder=0)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(loc="upper left", frameon=True, facecolor="#F8FAFC", edgecolor="#E2E8F0", fontsize=8)
    plt.tight_layout()
    chart3_path = os.path.join(ASSET_DIR, "chart_arr_model.png")
    plt.savefig(chart3_path, dpi=260)
    plt.close(fig)

    return chart1_path, chart2_path, chart3_path


# Helper UI builders
def set_slide_bg(slide, color: RGBColor):
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = color


def add_rect(slide, left, top, width, height, fill_rgb, border_rgb=None, border_pt=1.0, rounded=True):
    shape_type = MSO_SHAPE.ROUNDED_RECTANGLE if rounded else MSO_SHAPE.RECTANGLE
    shp = slide.shapes.add_shape(shape_type, Inches(left), Inches(top), Inches(width), Inches(height))
    shp.fill.solid()
    shp.fill.fore_color.rgb = fill_rgb
    if border_rgb:
        shp.line.color.rgb = border_rgb
        shp.line.width = Pt(border_pt)
    else:
        shp.line.fill.background()
    if rounded and len(shp.adjustments) > 0:
        shp.adjustments[0] = 0.04
    return shp


def add_textbox(slide, left, top, width, height, text, size=14, bold=False, color=INK, align=PP_ALIGN.LEFT, italic=False):
    tb = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = Inches(0.03)
    tf.margin_right = Inches(0.03)
    tf.margin_top = Inches(0.02)
    tf.margin_bottom = Inches(0.02)
    lines = text.split("\n")
    for idx, line in enumerate(lines):
        p = tf.paragraphs[0] if idx == 0 else tf.add_paragraph()
        p.alignment = align
        p.space_after = Pt(2)
        run = p.add_run()
        run.text = line
        run.font.name = FONT_MAIN
        run.font.size = Pt(size)
        run.font.bold = bold
        run.font.italic = italic
        run.font.color.rgb = color
    return tb


def add_bullets(slide, left, top, width, height, items, size=12.5, color=INK, space_after=6):
    tb = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = Inches(0.04)
    tf.margin_right = Inches(0.04)
    tf.margin_top = Inches(0.02)
    tf.margin_bottom = Inches(0.02)
    for idx, (lead, body) in enumerate(items):
        p = tf.paragraphs[0] if idx == 0 else tf.add_paragraph()
        p.space_after = Pt(space_after)
        r1 = p.add_run()
        r1.text = f"▸ {lead}: "
        r1.font.name = FONT_MAIN
        r1.font.size = Pt(size)
        r1.font.bold = True
        r1.font.color.rgb = NAVY

        r2 = p.add_run()
        r2.text = body
        r2.font.name = FONT_MAIN
        r2.font.size = Pt(size)
        r2.font.bold = False
        r2.font.color.rgb = color
    return tb


def add_header(slide, section_pill: str, title: str, subtitle: str, page_num: int):
    # Top accent bar
    add_rect(slide, 0, 0, 13.333, 0.08, CYAN, rounded=False)

    # Section Pill
    pill_w = max(2.3, len(section_pill) * 0.095 + 0.45)
    pill = add_rect(slide, 0.60, 0.30, pill_w, 0.32, CYAN_SOFT, border_rgb=CYAN, border_pt=1.0, rounded=True)
    if len(pill.adjustments) > 0:
        pill.adjustments[0] = 0.45
    add_textbox(slide, 0.65, 0.33, pill_w - 0.1, 0.26, section_pill, size=9.5, bold=True, color=NAVY, align=PP_ALIGN.CENTER)

    # Top-right brand stamp
    add_textbox(slide, 9.8, 0.31, 2.95, 0.28, "PaytmAI VyaparVoice · Track 1", size=9.5, bold=True, color=MUTED, align=PP_ALIGN.RIGHT)

    # Action Headline
    add_textbox(slide, 0.60, 0.70, 12.1, 0.48, title, size=22.5, bold=True, color=INK)
    add_textbox(slide, 0.60, 1.16, 12.1, 0.34, subtitle, size=12.0, bold=False, color=MUTED)

    # Subtle Footer
    add_rect(slide, 0.60, 7.08, 12.13, 0.015, BORDER, rounded=False)
    add_textbox(
        slide,
        0.60,
        7.13,
        8.5,
        0.26,
        "Paytm Build for India AI Hackathon – Bengaluru Edition  |  Team SemiTechnical (Kevin Joseph)",
        size=8.8,
        color=MUTED,
    )
    add_textbox(slide, 11.5, 7.13, 1.23, 0.26, f"Slide {page_num} / 9", size=8.8, bold=True, color=NAVY, align=PP_ALIGN.RIGHT)


def add_notes(slide, text: str):
    notes_slide = slide.notes_slide
    notes_slide.notes_text_frame.text = text


def build_presentation():
    chart1, chart2, chart3 = generate_charts()

    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    # =========================================================================
    # SLIDE 1: TITLE SLIDE (Dark Paytm Navy Hero)
    # =========================================================================
    s1 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s1, NAVY_DARK)

    # Top cyan ribbon & right geometric accent panel
    add_rect(s1, 0, 0, 13.333, 0.12, CYAN, rounded=False)
    add_rect(s1, 8.75, 0.75, 4.05, 5.95, NAVY, border_rgb=CYAN, border_pt=1.5, rounded=True)

    # Hackathon Badge
    add_rect(s1, 0.75, 0.80, 7.35, 0.42, NAVY, border_rgb=CYAN, border_pt=1.2, rounded=True)
    add_textbox(
        s1, 0.90, 0.88, 7.10, 0.30,
        "PAYTM BUILD FOR INDIA AI HACKATHON · BENGALURU EDITION  |  TRACK 1",
        size=10.5, bold=True, color=CYAN
    )

    # Main Title
    add_textbox(s1, 0.75, 1.55, 7.6, 0.85, "PaytmAI VyaparVoice", size=42, bold=True, color=WHITE)
    add_textbox(
        s1, 0.75, 2.40, 7.6, 0.75,
        "The Proactive Voice Growth, Operations & Retention Autopilot for Every Paytm Merchant",
        size=18.5, bold=True, color=CYAN
    )
    add_textbox(
        s1, 0.75, 3.25, 7.5, 0.85,
        "Transforming 1.57 Crore Paytm Soundboxes from passive payment speakers into active vernacular business partners — turning UPI history into verified repeat sales, smarter stock prep, and happier customers in 60 seconds a day.",
        size=12.8, color=RGBColor(0xCB, 0xD5, 0xE1)
    )

    # 3 Value Proof Badges on Left
    badges_s1 = [
        ("01 · Vernacular Voice-First", "Kannada, Hindi & English closing pitch; zero typing"),
        ("02 · Guardrailed by Design", "DPDP consent, ₹300 hard cap & ≤22% margin floor"),
        ("03 · Causal Holdout ROI", "Built-in 80/20 control split proving 5.8x net ₹ lift"),
    ]
    for i, (b_head, b_sub) in enumerate(badges_s1):
        bx = 0.75 + i * 2.55
        add_rect(s1, bx, 4.35, 2.40, 1.08, NAVY, border_rgb=RGBColor(0x1E, 0x40, 0xAF), border_pt=1.0)
        add_textbox(s1, bx + 0.12, 4.45, 2.16, 0.30, b_head, size=10.8, bold=True, color=WHITE)
        add_textbox(s1, bx + 0.12, 4.78, 2.16, 0.55, b_sub, size=9.8, color=RGBColor(0xBA, 0xE6, 0xFD))

    # Team Info Card at Bottom Left
    add_rect(s1, 0.75, 5.75, 7.55, 0.95, RGBColor(0x00, 0x12, 0x35), border_rgb=CYAN, border_pt=1.0)
    add_textbox(s1, 0.95, 5.86, 3.6, 0.32, "TEAM: SemiTechnical", size=14, bold=True, color=WHITE)
    add_textbox(s1, 0.95, 6.22, 4.8, 0.30, "Builder: Kevin Joseph  ·  Bengaluru, India", size=12, color=CYAN)
    add_textbox(s1, 5.10, 5.92, 3.00, 0.56, "Track 1: Merchant Growth AI\nWorking MVP Prototype Included", size=10.5, bold=True, color=RGBColor(0x6E, 0xE7, 0xB7), align=PP_ALIGN.RIGHT)

    # Right Side: Simulated AI Soundbox Visual Card
    add_textbox(s1, 9.05, 1.02, 3.45, 0.32, "PAYTM AI SOUNDBOX · 8:30 PM", size=11, bold=True, color=CYAN, align=PP_ALIGN.CENTER)
    add_rect(s1, 9.05, 1.45, 3.45, 1.25, RGBColor(0x05, 0x11, 0x26), border_rgb=CYAN, border_pt=1.2)
    add_textbox(s1, 9.20, 1.55, 3.15, 0.28, "LCD · SRI KRISHNA DARSHINI", size=9.5, bold=True, color=CYAN)
    add_textbox(s1, 9.20, 1.85, 3.15, 0.42, "+₹1,740 Net Sales Lift", size=18, bold=True, color=RGBColor(0x34, 0xD3, 0x99))
    add_textbox(s1, 9.20, 2.28, 3.15, 0.28, "40 Regulars Eligible · ₹300 Max Cap", size=9.8, color=RGBColor(0x94, 0xA3, 0xB8))

    add_rect(s1, 9.05, 2.92, 3.45, 2.15, RGBColor(0x07, 0x22, 0x5B), border_rgb=RGBColor(0x38, 0xBD, 0xF8), border_pt=0.8)
    add_textbox(s1, 9.20, 3.04, 3.15, 0.28, "▸ EVENING KANNADA / EN BRIEF", size=9.5, bold=True, color=CYAN)
    add_textbox(
        s1, 9.20, 3.35, 3.15, 1.60,
        "\"Namaskara Ramesh avare! 40 regular evening buyers haven't visited in 18 days. Send ₹25 UPI cashback on ₹150+ bill? Max spend locked at ₹300.\"\n▸ Merchant Reply: \"Haudu, kaluhisi!\"",
        size=10.3, italic=True, color=WHITE
    )

    add_rect(s1, 9.05, 5.30, 3.45, 1.10, EMER_SOFT, border_rgb=EMERALD, border_pt=1.2)
    add_textbox(s1, 9.20, 5.42, 3.15, 0.30, "✔ WORKING PROTOTYPE BUILT", size=10.5, bold=True, color=EMERALD, align=PP_ALIGN.CENTER)
    add_textbox(s1, 9.20, 5.74, 3.15, 0.55, "FastAPI + SQLite + Indic Voice +\n5-Rule Guardrails + Holdout Engine", size=10.0, bold=True, color=INK, align=PP_ALIGN.CENTER)

    add_notes(s1, "Hi everyone, I'm Kevin Joseph from Team SemiTechnical. For Track 1 (Merchant Growth AI), we built PaytmAI VyaparVoice — turning Paytm's 1.57 crore Soundboxes into a proactive, vernacular voice growth and operations copilot.")

    # =========================================================================
    # SLIDE 2: PROBLEM STATEMENT
    # =========================================================================
    s2 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s2, BG_LIGHT)
    add_header(
        s2,
        "01 · PROBLEM STATEMENT",
        "1.57 Cr Merchants Accept Digital Payments — Yet Run Blind on Retention & Ops",
        "Paytm digitized payment collection across India, but small shopkeepers still lose 25–35% of repeat buyers silently.",
        2,
    )

    # Left Column: 3 Crisp Problem Cards
    prob_cards = [
        (
            "1. Silent Repeat-Customer Churn (28–35% Annual Attrition)",
            "A busy shop processes 150–300 UPI scans daily, but treats every QR payment as an isolated alert. Merchants never notice when loyal ₹2,000/month regulars quietly stop visiting until monthly cashflow drops.",
            AMBER, AMB_SOFT
        ),
        (
            "2. Zero Time or Literacy for BI Dashboards & Chat Prompts",
            "Kirana, darshini, and pharmacy owners stand at busy counters 12+ hours/day. Existing 'analytics apps' fail (<8% WAU) because merchants won't type prompts, export CSVs, or configure CRM rules.",
            NAVY, CYAN_SOFT
        ),
        (
            "3. Predictable Dead Hours & Unplanned Rush Stockouts",
            "Stores suffer a 60–70% footfall drop every afternoon (3–5 PM) causing perishable waste, yet run out of high-velocity staples (milk, batter) on payday weekends due to guesswork ordering.",
            CYAN_DARK, INDIGO_SF
        ),
    ]
    for idx, (p_title, p_desc, accent_c, bg_c) in enumerate(prob_cards):
        cy = 1.65 + idx * 1.72
        add_rect(s2, 0.60, cy, 6.35, 1.54, WHITE, border_rgb=BORDER, border_pt=1.0)
        add_rect(s2, 0.60, cy, 0.10, 1.54, accent_c, rounded=False)
        add_textbox(s2, 0.84, cy + 0.14, 5.95, 0.34, p_title, size=13.5, bold=True, color=NAVY)
        add_textbox(s2, 0.84, cy + 0.52, 5.95, 0.90, p_desc, size=11.3, color=MUTED)

    # Right Column Top: Matplotlib Hourly Chart Card
    add_rect(s2, 7.15, 1.65, 5.58, 3.18, WHITE, border_rgb=BORDER, border_pt=1.0)
    s2.shapes.add_picture(chart1, Inches(7.24), Inches(1.74), width=Inches(5.40))

    # Right Column Bottom: Real Persona + Paytm Scale Opportunity Box
    add_rect(s2, 7.15, 5.00, 5.58, 1.83, NAVY_DARK, border_rgb=CYAN, border_pt=1.2)
    add_textbox(s2, 7.35, 5.14, 5.20, 0.30, "GROUND REALITY · BENGALURU MERCHANT PERSONA", size=10.5, bold=True, color=CYAN)
    add_textbox(
        s2, 7.35, 5.46, 5.20, 0.72,
        "Ramesh Rao · Sri Krishna Darshini & Provisions (Indiranagar)\nProcesses ~917 Paytm UPI scans/month (₹1.75L GMV), yet had 48 regular evening buyers go silent for 18+ days without realizing it.",
        size=11.0, color=WHITE
    )
    # 3 Mini Ecosystem Stat Callouts
    stats_s2 = [("1.57 Cr", "Paytm Device Shops"), ("₹7.1L Cr", "Quarterly Merchant GMV"), ("< 7%", "Current Loan Penetration")]
    for i, (sv, sl) in enumerate(stats_s2):
        sx = 7.35 + i * 1.76
        add_textbox(s2, sx, 6.22, 1.65, 0.30, sv, size=14.5, bold=True, color=CYAN)
        add_textbox(s2, sx, 6.50, 1.65, 0.24, sl, size=8.8, color=RGBColor(0xCB, 0xD5, 0xE1))

    add_notes(s2, "Paytm already owns the storefront counter with 1.57 crore Soundboxes. Yet merchants lose 30% of repeat buyers silently and suffer 68% afternoon dead-hour drops because busy shopkeepers cannot read BI charts or type prompts.")

    # =========================================================================
    # SLIDE 3: PROPOSED SOLUTION (3-PILLAR TRACK 1 COVERAGE)
    # =========================================================================
    s3 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s3, BG_LIGHT)
    add_header(
        s3,
        "02 · PROPOSED SOLUTION",
        "PaytmAI VyaparVoice: Proactive Voice Partner on Every Counter",
        "Directly engineered around all 3 pillars of Track 1 — Grow Business, Manage Operations, and Serve Customers Better.",
        3,
    )

    pillars = [
        (
            "PILLAR 1 · GROW BUSINESS",
            "Win-Back & Dead-Hour Autopilot",
            NAVY,
            [
                ("Silent Churn Radar", "Flags high-frequency UPI payers inactive for 15–30 days automatically."),
                ("Dead-Hour Flash Boost", "Fills 3–5 PM slow slots with hyperlocal combo nudges to afternoon buyers."),
                ("1-Tap UPI Cashback Pass", "Auto-redeemed on next Paytm QR scan — zero paper coupons or cashier friction."),
                ("Causal Holdout Proof", "Holds 20% silent control group to prove exact net incremental ₹ earned."),
            ],
        ),
        (
            "PILLAR 2 · MANAGE OPERATIONS",
            "Predictive Rush & Supplier Copilot",
            CYAN_DARK,
            [
                ("Payday & Weekend Forecasting", "Detects +28% end-of-month & weather spikes from historical scan velocity."),
                ("1-Command Supplier PO", "Sends pre-filled WhatsApp restock orders (milk, batter, staples) to local vendors."),
                ("Perishable Margin Guard", "Triggers evening clearance bundles on slow-moving fresh stock before closing."),
                ("Working-Capital Readiness", "Tracks cashflow & EDI coverage to unlock pre-approved Paytm partner credit."),
            ],
        ),
        (
            "PILLAR 3 · SERVE CUSTOMERS",
            "Vernacular Post-Visit Delight",
            EMERALD,
            [
                ("Queue-Delay Detection", "Spots unusually slow peak-hour clusters & 3-star Paytm payment feedback tags."),
                ("Instant Goodwill Recovery", "Dispatches merchant-signed Kannada/Hindi apology + ₹30 coffee pass in 1 tap."),
                ("Zero-App Loyalty Milestones", "Automatically celebrates a regular's 10th UPI scan on Soundbox audio."),
                ("DPDP-Compliant Privacy", "Strictly honors customer opt-in & enforces 14-day anti-spam cooldowns."),
            ],
        ),
    ]

    for idx, (tag, head, col, bullets) in enumerate(pillars):
        px = 0.60 + idx * 4.12
        add_rect(s3, px, 1.68, 3.88, 3.92, WHITE, border_rgb=BORDER, border_pt=1.0)
        add_rect(s3, px, 1.68, 3.88, 0.10, col, rounded=False)
        add_textbox(s3, px + 0.18, 1.88, 3.52, 0.26, tag, size=9.8, bold=True, color=col)
        add_textbox(s3, px + 0.18, 2.14, 3.52, 0.38, head, size=14.5, bold=True, color=INK)
        add_bullets(s3, px + 0.16, 2.58, 3.56, 2.90, bullets, size=10.8, color=MUTED, space_after=7)

    # Bottom Principle Banner: Why Merchants Actually Use It
    add_rect(s3, 0.60, 5.80, 12.13, 1.06, NAVY_DARK, border_rgb=CYAN, border_pt=1.2)
    add_textbox(
        s3, 0.85, 5.92, 11.6, 0.32,
        "CORE DESIGN PRINCIPLE: \"ONE EVENING VOICE ACTION — NEVER ANOTHER DASHBOARD\"",
        size=12.0, bold=True, color=CYAN
    )
    add_textbox(
        s3, 0.85, 6.26, 11.6, 0.48,
        "Instead of expecting shopkeepers to analyze graphs, VyaparVoice speaks ONE high-confidence recommendation at 8:30 PM closing time in Kannada, Hindi, or English. The merchant simply says \"Haudu / Haan, bhej do\" — and AI executes end-to-end.",
        size=11.2, color=WHITE
    )

    add_notes(s3, "Our solution spans all three mandates of Track 1: automated churn win-back and dead-hour footfall to grow business, predictive supplier restocking to manage operations, and instant queue-delay recovery to serve customers better.")

    # =========================================================================
    # SLIDE 4: CLOSED-LOOP WORKFLOW & WORKING PROTOTYPE
    # =========================================================================
    s4 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s4, BG_LIGHT)
    add_header(
        s4,
        "02B · CLOSED-LOOP USER JOURNEY & LIVE MVP",
        "60 Seconds at Closing Time: From UPI Signal to Verified ₹1,740 Net Lift",
        "End-to-end workflow already running in our Working MVP Prototype (Sri Krishna Darshini, Indiranagar dataset).",
        4,
    )

    steps = [
        (
            "STEP 1 · 8:25 PM",
            "Zero-Entry UPI Scan",
            "SQLite/Postgres RFM engine scans 1,613 Paytm QR txns across 240 payers. Flags 48 evening regulars silent for 16–28 days.",
            NAVY
        ),
        (
            "STEP 2 · 8:29 PM",
            "5-Rule Policy Guardrail",
            "Filters to 40 DPDP-consented & cooldown-clear users. Verifies ₹25 off ₹150+ (16.7% ≤ 22% margin cap) & locks ₹300 max spend.",
            CYAN_DARK
        ),
        (
            "STEP 3 · 8:30 PM",
            "Vernacular Voice Pitch",
            "Soundbox speaks pitch in Kannada/Hindi/English. Merchant replies \"Haudu, approve!\" (or 1-tap). 32 nudged; 8 held in silent Control.",
            AMBER
        ),
        (
            "STEP 4 · +48 HOURS",
            "Causal ROI Verification",
            "12/32 nudged regulars scan & pay (37.5%) vs 1/8 Control (12.5%). Soundbox reports +₹1,740 net new sales on ₹300 spend (5.8x ROI).",
            EMERALD
        ),
    ]

    for idx, (st_tag, st_head, st_desc, st_col) in enumerate(steps):
        sx = 0.60 + idx * 3.08
        add_rect(s4, sx, 1.68, 2.88, 2.52, WHITE, border_rgb=st_col, border_pt=1.4)
        add_rect(s4, sx, 1.68, 2.88, 0.36, st_col, rounded=False)
        add_textbox(s4, sx + 0.12, 1.73, 2.64, 0.26, st_tag, size=10.0, bold=True, color=WHITE)
        add_textbox(s4, sx + 0.14, 2.14, 2.60, 0.34, st_head, size=13.5, bold=True, color=INK)
        add_textbox(s4, sx + 0.14, 2.52, 2.60, 1.55, st_desc, size=10.8, color=MUTED)
        if idx < 3:
            add_textbox(s4, sx + 2.89, 2.72, 0.20, 0.40, "➔", size=15, bold=True, color=CYAN_DARK, align=PP_ALIGN.CENTER)

    # Bottom Showcase: Live Working Prototype Verification Strip
    add_rect(s4, 0.60, 4.44, 12.13, 2.40, WHITE, border_rgb=NAVY, border_pt=1.2)
    add_rect(s4, 0.60, 4.44, 12.13, 0.40, NAVY, rounded=False)
    add_textbox(
        s4, 0.80, 4.50, 11.7, 0.28,
        "LIVE WORKING PROTOTYPE INCLUDED  ·  REAL FASTAPI + SQLITE COMPUTATION (ZERO HARDCODED MOCK NUMBERS)",
        size=10.5, bold=True, color=CYAN
    )

    mvp_cols = [
        (
            "01 · Interactive AI Soundbox Simulator",
            "• Live switch between English, Kannada (KN), and Hindi (HI) evening voice briefings.\n• Browser SpeechSynthesis + Microphone voice intent recognition ('Haudu / Haan, approve!').\n• Animated Soundbox LED + real-time LCD status readout."
        ),
        (
            "02 · Deterministic Policy Inspector",
            "• Displays exact pass/fail counts on every campaign card before merchant approval.\n• Enforces DPDP opt-in (43/48), 14d cooldown (40/43), ≤22% discount floor, and ₹300 hard liability cutoff."
        ),
        (
            "03 · 48-Hr Time-Travel & Ops Engine",
            "• 1-click simulation inserts redemption UPI scans into SQLite & computes causal lift vs 20% holdout.\n• Includes Weekend Dairy Supplier WhatsApp PO (+18L milk) & Queue-Delay Goodwill Recovery."
        ),
    ]
    for i, (m_head, m_body) in enumerate(mvp_cols):
        mx = 0.80 + i * 3.98
        add_textbox(s4, mx, 4.98, 3.78, 0.34, m_head, size=12.5, bold=True, color=NAVY)
        add_textbox(s4, mx, 5.34, 3.78, 1.38, m_body, size=10.5, color=MUTED)

    add_notes(s4, "Here is how a merchant experiences VyaparVoice in 60 seconds at 8:30 PM. Everything on this slide is already built and running in our live FastAPI + SQLite prototype.")

    # =========================================================================
    # SLIDE 5: TECHNOLOGY / TECH STACK USED
    # =========================================================================
    s5 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s5, BG_LIGHT)
    add_header(
        s5,
        "03 · TECHNOLOGY & TECH STACK USED",
        "Low-Latency, Guardrailed Agentic Architecture Built for Vernacular Scale",
        "LLMs handle natural vernacular conversation; deterministic Python engines govern money, consent, and math.",
        5,
    )

    layers = [
        (
            "LAYER 1 · MERCHANT & CUSTOMER TOUCHPOINTS",
            NAVY_DARK,
            [
                ("Paytm AI Soundbox 4G", "Scheduled evening audio briefing + single-button / voice confirmation"),
                ("Paytm for Business PWA", "Lightweight React/HTML5 visual companion card & live ROI tracker"),
                ("Paytm App & WhatsApp Cloud", "Instant UPI Cashback Pass delivery & 1-tap supplier WhatsApp POs"),
            ],
        ),
        (
            "LAYER 2 · INDIC VOICE & AGENTIC INTELLIGENCE LAYER",
            NAVY,
            [
                ("Sarvam AI + Web Speech", "Natural Kannada, Hindi, Tamil & Indian-English ASR + TTS (<400ms latency)"),
                ("SLM / LLM Intent Router", "Llama-3.3 / Qwen structured tool-calling via Groq for ultra-low inference cost"),
                ("Semantic Store Memory", "Cognee / Vector store retaining merchant margin preferences & local calendar"),
            ],
        ),
        (
            "LAYER 3 · DETERMINISTIC POLICY, RFM & CAUSAL ENGINE (CORE)",
            CYAN_DARK,
            [
                ("Python FastAPI Core", "Async microservices computing RFM cohorts & hourly velocity troughs"),
                ("5-Rule Policy Engine", "Hard deterministic checks: DPDP consent, 14d cooldown, margin floor & ₹ cap"),
                ("80/20 Holdout Attribution", "Randomized control split & redemption matcher calculating true incremental ₹"),
            ],
        ),
        (
            "LAYER 4 · TRANSACTION DATA & EVENT ORCHESTRATION",
            EMERALD,
            [
                ("PostgreSQL / SQLite Ledger", "Paytm QR UPI scan stream, customer consent state & immutable audit trail"),
                ("Redis Coupon Counter", "Sub-millisecond atomic redemption counter enforcing instant ₹300 budget cutoff"),
                ("n8n Workflow Automation", "8:30 PM closing cron triggers, 48h ROI report callbacks & supplier alerts"),
            ],
        ),
    ]

    for idx, (l_title, l_col, l_boxes) in enumerate(layers):
        ly = 1.62 + idx * 1.32
        add_rect(s5, 0.60, ly, 12.13, 1.18, WHITE, border_rgb=BORDER, border_pt=1.0)
        add_rect(s5, 0.60, ly, 2.75, 1.18, l_col, rounded=False)
        add_textbox(s5, 0.74, ly + 0.24, 2.48, 0.72, l_title, size=10.5, bold=True, color=WHITE)

        for j, (b_name, b_desc) in enumerate(l_boxes):
            bx = 3.52 + j * 3.04
            add_rect(s5, bx, ly + 0.12, 2.90, 0.94, BG_LIGHT, border_rgb=BORDER, border_pt=0.8)
            add_textbox(s5, bx + 0.10, ly + 0.18, 2.70, 0.28, b_name, size=11.0, bold=True, color=NAVY)
            add_textbox(s5, bx + 0.10, ly + 0.46, 2.70, 0.52, b_desc, size=9.6, color=MUTED)

    add_notes(s5, "Our architecture separates probabilistic AI from financial execution: Sarvam AI and SLMs handle vernacular voice, while a deterministic Python guardrail engine and Redis atomic counters guarantee zero budget overruns or hallucinations.")

    # =========================================================================
    # SLIDE 6: USP (UNIQUE SELLING PROPOSITION)
    # =========================================================================
    s6 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s6, BG_LIGHT)
    add_header(
        s6,
        "04 · UNIQUE SELLING PROPOSITION (USP)",
        "Why VyaparVoice Wins Where Dashboards & Generic AI Chatbots Fail",
        "Purpose-built around Paytm's unfair hardware + UPI network moat and Indian shopkeeper behavior.",
        6,
    )

    # Comparison Table
    tbl_shape = s6.shapes.add_table(6, 4, Inches(0.60), Inches(1.68), Inches(12.13), Inches(3.65))
    tbl = tbl_shape.table
    col_widths = [Inches(2.35), Inches(2.90), Inches(2.90), Inches(3.98)]
    for i, cw in enumerate(col_widths):
        tbl.columns[i].width = cw

    headers = [
        "Dimension",
        "Traditional BI / Khata Apps",
        "Generic 'Chat-With-Data' AI",
        "PaytmAI VyaparVoice (Ours)",
    ]
    rows_data = [
        [
            "Merchant Effort",
            "Manual entry + complex charts (<8% weekly active usage)",
            "Requires typing prompts & asking the right business question",
            "Proactive 20-sec Kannada/Hindi Soundbox briefing + 'Haan' voice approval",
        ],
        [
            "Customer Data Source",
            "Manual phonebook / incomplete paper bills",
            "Disconnected from real payment identity",
            "Zero-entry Paytm QR repeat-payer graph across 1.57 Cr storefronts",
        ],
        [
            "Financial & Legal Safety",
            "Static rules; manual coupon abuse risk",
            "LLM hallucination risk on discounts & spam violations",
            "Deterministic 5-rule policy engine (DPDP opt-in, margin cap, ₹300 cutoff)",
        ],
        [
            "Action Execution",
            "Passive insights only — merchant must act alone",
            "Text suggestions only; no payment rail hook",
            "Closed-loop Paytm UPI Cashback Pass + 1-tap WhatsApp Supplier PO",
        ],
        [
            "Proof of ROI",
            "Vanity SMS sent / message open counts",
            "No causal measurement",
            "Built-in 80/20 Holdout Control Split proving true net incremental ₹",
        ],
    ]

    for c_idx, h_text in enumerate(headers):
        cell = tbl.cell(0, c_idx)
        cell.fill.solid()
        cell.fill.fore_color.rgb = NAVY_DARK if c_idx < 3 else CYAN_DARK
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        p = cell.text_frame.paragraphs[0]
        p.text = h_text
        p.font.name = FONT_MAIN
        p.font.size = Pt(11.0)
        p.font.bold = True
        p.font.color.rgb = WHITE

    for r_idx, r_vals in enumerate(rows_data, start=1):
        for c_idx, val in enumerate(r_vals):
            cell = tbl.cell(r_idx, c_idx)
            cell.fill.solid()
            if c_idx == 3:
                cell.fill.fore_color.rgb = EMER_SOFT
            else:
                cell.fill.fore_color.rgb = WHITE if r_idx % 2 == 1 else RGBColor(0xF8, 0xFA, 0xFC)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            p = cell.text_frame.paragraphs[0]
            p.text = val
            p.font.name = FONT_MAIN
            p.font.size = Pt(10.0)
            p.font.bold = c_idx in (0, 3)
            p.font.color.rgb = INK if c_idx in (0, 3) else MUTED

    # 3 Bottom Moat Callout Cards
    moats = [
        ("1. Hardware Distribution Moat", "Rides on Paytm's deployed 1.57 Cr Soundboxes — zero extra hardware capex or new app install."),
        ("2. Zero-Friction Redemption", "Cashback unlocks automatically when the customer scans the merchant's Paytm QR — zero cashier training."),
        ("3. Trust Through Honest Math", "Showing holdout-verified net ₹ lift builds lasting merchant trust to renew SaaS every month."),
    ]
    for i, (m_t, m_d) in enumerate(moats):
        mx = 0.60 + i * 4.12
        add_rect(s6, mx, 5.54, 3.88, 1.30, WHITE, border_rgb=CYAN, border_pt=1.2)
        add_textbox(s6, mx + 0.16, 5.66, 3.56, 0.30, m_t, size=12.0, bold=True, color=NAVY)
        add_textbox(s6, mx + 0.16, 5.98, 3.56, 0.74, m_d, size=10.3, color=MUTED)

    add_notes(s6, "Our biggest USP is combining zero-typing vernacular Soundbox interaction with Paytm's QR repeat-payer graph, deterministic financial guardrails, and true 80/20 causal holdout attribution.")

    # =========================================================================
    # SLIDE 7: IMPACT & BENEFITS
    # =========================================================================
    s7 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s7, BG_LIGHT)
    add_header(
        s7,
        "05 · IMPACT & BENEFITS",
        "Win-Win Flywheel: Verified Rupee Profit for Shops & Stickiness for Paytm",
        "Every incremental repeat visit grows merchant income while compounding Paytm's GMV, device ARPU, and credit data.",
        7,
    )

    # Left Top: Merchant Impact Card
    add_rect(s7, 0.60, 1.68, 6.45, 2.50, WHITE, border_rgb=BORDER, border_pt=1.0)
    add_rect(s7, 0.60, 1.68, 0.10, 2.50, EMERALD, rounded=False)
    add_textbox(s7, 0.84, 1.80, 6.0, 0.32, "FOR PAYTM MERCHANTS (1.57 CR SMBs)", size=12.5, bold=True, color=EMERALD)
    add_bullets(
        s7, 0.84, 2.16, 6.05, 1.90,
        [
            ("+14% to +22% Repeat Visits", "Recovers silent churned regulars before they switch permanently to competitors."),
            ("5.8x Verified Campaign ROI", "+₹1,740 net incremental sales on ₹300 capped spend in 48h MVP simulation."),
            ("< 60 Seconds Daily Effort", "100% hands-free Kannada/Hindi voice workflow while closing the shutter."),
            ("-18% Dead-Hour & Stock Loss", "Afternoon combo nudges + predictive weekend dairy/staple POs protect margins."),
        ],
        size=10.8, color=MUTED, space_after=5
    )

    # Left Bottom: Paytm Ecosystem Impact Card
    add_rect(s7, 0.60, 4.34, 6.45, 2.50, WHITE, border_rgb=BORDER, border_pt=1.0)
    add_rect(s7, 0.60, 4.34, 0.10, 2.50, NAVY, rounded=False)
    add_textbox(s7, 0.84, 4.46, 6.0, 0.32, "FOR PAYTM ECOSYSTEM (STRATEGIC FLYWHEEL)", size=12.5, bold=True, color=NAVY)
    add_bullets(
        s7, 0.84, 4.82, 6.05, 1.90,
        [
            ("-35% Soundbox Churn", "Transforms Soundbox from a ₹100/mo cost center into a visible profit-generating partner."),
            ("+12–15% Store QR GMV", "Cashback passes require payment via Paytm UPI QR, capturing greater counter share."),
            ("7% → 15% Lending Funnel", "Verified retention stability & cashflow curves unlock low-risk merchant loan distribution."),
            ("Consumer App Stickiness", "Hyperlocal rewards from neighborhood darshinis & kiranas boost daily Paytm app opens."),
        ],
        size=10.8, color=MUTED, space_after=5
    )

    # Right Side: Holdout Chart + Big Metric Tiles
    add_rect(s7, 7.25, 1.68, 5.48, 3.22, WHITE, border_rgb=BORDER, border_pt=1.0)
    s7.shapes.add_picture(chart2, Inches(7.34), Inches(1.76), width=Inches(5.30))

    kpi_s7 = [
        ("5.8x", "Avg Net Campaign ROI", EMERALD),
        ("+79%", "Soundbox ARPU Lift", NAVY),
        ("< ₹2", "Monthly AI Cost / Shop", CYAN_DARK),
    ]
    for i, (kv, kl, kc) in enumerate(kpi_s7):
        kx = 7.25 + i * 1.88
        add_rect(s7, kx, 5.08, 1.72, 1.76, WHITE, border_rgb=kc, border_pt=1.4)
        add_textbox(s7, kx + 0.08, 5.36, 1.56, 0.56, kv, size=24, bold=True, color=kc, align=PP_ALIGN.CENTER)
        add_textbox(s7, kx + 0.08, 6.02, 1.56, 0.58, kl, size=10.5, bold=True, color=MUTED, align=PP_ALIGN.CENTER)

    add_notes(s7, "For merchants, VyaparVoice delivers a 5.8x verified return in under 60 seconds a day. For Paytm, it slashes Soundbox churn, boosts QR GMV share, and expands high-margin merchant credit distribution.")

    # =========================================================================
    # SLIDE 8: BUSINESS MODEL
    # =========================================================================
    s8 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s8, BG_LIGHT)
    add_header(
        s8,
        "06 · BUSINESS MODEL",
        "Zero-CAC SaaS + Pay-for-Success Take-Rate Scaling to ₹243 Cr+ ARR",
        "Monetizes Paytm's existing 1.57 Cr merchant billing rail with >78% software gross margins.",
        8,
    )

    # Left Column: 3 Revenue Streams + Unit Economics Box
    rev_streams = [
        (
            "1. Soundbox 'Growth Pro' SaaS Add-On — ₹79 / Month",
            "Bundled onto existing ₹100/mo Soundbox subscription (+79% device ARPU uplift) with near-zero customer acquisition cost. First 2 win-back campaigns free to prove ROI before billing.",
            NAVY
        ),
        (
            "2. Pay-for-Success Redemption Micro-Fee — 5% of Attributed Promo Bill",
            "Charged ONLY when a nudged customer scans & pays at the counter (e.g., ~₹9.50 fee on a ₹190 recovered bill). 100% risk-free alignment for small shopkeepers.",
            CYAN_DARK
        ),
        (
            "3. Merchant Lending Origination Uplift — 1.5% to 2.5% Partner Fee",
            "High-retention merchants growing GMV via VyaparVoice pre-qualify for Paytm's asset-light NBFC/bank working-capital loans, expanding Paytm's highest-margin revenue engine.",
            EMERALD
        ),
    ]
    for idx, (r_head, r_desc, r_col) in enumerate(rev_streams):
        ry = 1.68 + idx * 1.34
        add_rect(s8, 0.60, ry, 6.35, 1.20, WHITE, border_rgb=BORDER, border_pt=1.0)
        add_rect(s8, 0.60, ry, 0.10, 1.20, r_col, rounded=False)
        add_textbox(s8, 0.82, ry + 0.12, 5.98, 0.30, r_head, size=12.2, bold=True, color=r_col)
        add_textbox(s8, 0.82, ry + 0.44, 5.98, 0.66, r_desc, size=10.4, color=MUTED)

    # Unit Economics Strip Bottom Left
    add_rect(s8, 0.60, 5.74, 6.35, 1.10, NAVY_DARK, border_rgb=CYAN, border_pt=1.0)
    add_textbox(s8, 0.80, 5.84, 5.95, 0.28, "UNIT ECONOMICS PER ACTIVE MERCHANT / MONTH (~81% GROSS MARGIN)", size=10.0, bold=True, color=CYAN)
    add_textbox(
        s8, 0.80, 6.14, 5.95, 0.58,
        "Blended Monthly ARPU: ₹258/shop (₹79 SaaS + ₹102 Promo Fee + ₹77 Credit Uplift)\nMonthly COGS: ~₹48/shop (SLM inference ₹1.80 + Cached Indic TTS ₹3.20 + WhatsApp/Push ₹43)",
        size=10.3, color=WHITE
    )

    # Right Column: ARR Chart + Base Case Summary
    add_rect(s8, 7.15, 1.68, 5.58, 3.42, WHITE, border_rgb=BORDER, border_pt=1.0)
    s8.shapes.add_picture(chart3, Inches(7.24), Inches(1.76), width=Inches(5.40))

    add_rect(s8, 7.15, 5.26, 5.58, 1.58, EMER_SOFT, border_rgb=EMERALD, border_pt=1.2)
    add_textbox(s8, 7.35, 5.38, 5.20, 0.30, "BASE CASE AT JUST 5% DEVICE ADOPTION (7.85 LAKH SHOPS)", size=10.5, bold=True, color=EMERALD)
    add_textbox(s8, 7.35, 5.72, 5.20, 0.40, "₹243 Crore High-Margin ARR", size=19.5, bold=True, color=INK)
    add_textbox(
        s8, 7.35, 6.18, 5.20, 0.54,
        "Directly supports Paytm's AI commerce & cloud monetization roadmap with zero balance-sheet credit risk.",
        size=10.3, color=MUTED
    )

    add_notes(s8, "Because Paytm already bills 1.57 crore device merchants monthly, our CAC is near zero. Even a conservative 5% adoption yields ₹243 Crore in high-margin ARR across SaaS, performance fees, and partner credit origination.")

    # =========================================================================
    # SLIDE 9: EXECUTION ROADMAP & READY FOR DEMO (Closing Dark Navy Slide)
    # =========================================================================
    s9 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s9, NAVY_DARK)
    add_rect(s9, 0, 0, 13.333, 0.10, CYAN, rounded=False)

    add_rect(s9, 0.65, 0.40, 3.60, 0.34, NAVY, border_rgb=CYAN, border_pt=1.0)
    add_textbox(s9, 0.75, 0.44, 3.40, 0.26, "07 · EXECUTION ROADMAP & LIVE DEMO", size=9.8, bold=True, color=CYAN, align=PP_ALIGN.CENTER)

    add_textbox(s9, 0.65, 0.90, 12.0, 0.52, "Built Today, Engineered to Scale to Millions of Storefronts", size=26, bold=True, color=WHITE)
    add_textbox(s9, 0.65, 1.44, 12.0, 0.34, "From working Bengaluru hackathon vertical slice to pan-India 11-language Soundbox deployment.", size=12.5, color=RGBColor(0xBA, 0xE6, 0xFD))

    phases = [
        (
            "PHASE 1 · BUILT TODAY (MVP)",
            "Working Vertical Slice Ready",
            CYAN,
            [
                "Real SQLite UPI ledger (240 payers, 1,613 scans) + FastAPI RFM & hourly trough engine",
                "Kannada, Hindi & English AI Soundbox voice simulator + speech command approval",
                "5-rule deterministic guardrail engine + 48h causal holdout ROI simulator (5.8x ROI)",
            ],
        ),
        (
            "PHASE 2 · DAYS 1–45 PILOT",
            "Bengaluru 1,000-Store Live Beta",
            RGBColor(0x38, 0xBD, 0xF8),
            [
                "Deploy across 1,000 F&B, kirana & pharmacy Soundbox merchants in Bengaluru",
                "Integrate live Sarvam AI streaming audio + Paytm UPI Dynamic Offer Ledger",
                "Validate 30-day repeat GMV lift, coupon auto-cutoff & merchant renewal conversion",
            ],
        ),
        (
            "PHASE 3 · DAYS 45–120 SCALE",
            "Pan-India 11-Language Rollout",
            RGBColor(0x34, 0xD3, 0x99),
            [
                "Expand across all 11 Soundbox languages on Paytm's 1.57 Cr merchant device fleet",
                "Launch hyperlocal distributor B2B restock marketplace & FMCG brand-funded offers",
                "Feed verified retention scores into Paytm Intelligence (Pi) credit distribution",
            ],
        ),
    ]

    for idx, (p_tag, p_head, p_col, p_items) in enumerate(phases):
        px = 0.65 + idx * 4.10
        add_rect(s9, px, 2.02, 3.85, 3.25, NAVY, border_rgb=p_col, border_pt=1.3)
        add_textbox(s9, px + 0.18, 2.18, 3.50, 0.28, p_tag, size=10.0, bold=True, color=p_col)
        add_textbox(s9, px + 0.18, 2.48, 3.50, 0.36, p_head, size=14.5, bold=True, color=WHITE)
        for j, item in enumerate(p_items):
            add_textbox(s9, px + 0.18, 2.96 + j * 0.72, 3.50, 0.66, f"✔  {item}", size=10.5, color=RGBColor(0xE2, 0xE8, 0xF0))

    # Closing Callout Footer Box
    add_rect(s9, 0.65, 5.58, 12.05, 1.32, RGBColor(0x00, 0x11, 0x33), border_rgb=CYAN, border_pt=1.4)
    add_textbox(s9, 0.90, 5.76, 7.6, 0.38, "PaytmAI VyaparVoice · Every Merchant's AI Growth Partner", size=16.0, bold=True, color=WHITE)
    add_textbox(
        s9, 0.90, 6.22, 7.6, 0.42,
        "Paytm Build for India AI Hackathon – Bengaluru Edition  |  Track 1: Merchant Growth AI",
        size=11.5, color=CYAN
    )
    add_textbox(
        s9, 8.55, 5.74, 3.90, 0.96,
        "Team: SemiTechnical\nBuilder: Kevin Joseph\nStatus: Pitch + Live MVP Ready",
        size=11.8, bold=True, color=RGBColor(0x6E, 0xE7, 0xB7), align=PP_ALIGN.RIGHT
    )

    add_notes(s9, "Thank you! Our working MVP is already live today with real SQLite cohort analytics, Kannada/Hindi/English Soundbox voice briefings, deterministic guardrails, and causal ROI proof. We're excited to build this live in Bengaluru!")

    prs.save(PPTX_PATH)
    print("Saved PPTX:", PPTX_PATH)


if __name__ == "__main__":
    build_presentation()
