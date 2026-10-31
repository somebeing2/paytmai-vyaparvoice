#!/usr/bin/env python3
"""Render docs/AI_TOOLS_NOTE.md into a clean, print-ready docs/AI_TOOLS_NOTE.pdf.

Reads docs/AI_TOOLS_NOTE.md directly so markdown and PDF stay 100% identical in content,
validates formatting hygiene (zero em/en dashes, zero emojis), and prints via headless Chromium
with Noto Sans / Devanagari / Kannada font support.
"""

from __future__ import annotations

import html
import pathlib
import re
import shutil
import sys

from playwright.sync_api import sync_playwright

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.copy_lint import find_formatting_violations  # noqa: E402

MD_PATH = REPO_ROOT / "docs" / "AI_TOOLS_NOTE.md"
PDF_PATH = REPO_ROOT / "docs" / "AI_TOOLS_NOTE.pdf"


def inline_md(text: str) -> str:
    esc = html.escape(text, quote=False)
    # Inline code first so bold inside code is not mangled
    code_tokens = []

    def _save_code(m: re.Match) -> str:
        code_tokens.append(f"<code>{m.group(1)}</code>")
        return f"\x00CODE{len(code_tokens) - 1}\x00"

    esc = re.sub(r"`([^`]+)`", _save_code, esc)
    esc = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", esc)
    esc = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", esc)
    for idx, tok in enumerate(code_tokens):
        esc = esc.replace(f"\x00CODE{idx}\x00", tok)
    return esc


def md_to_html_body(md_text: str) -> str:
    lines = md_text.splitlines()
    out = []
    in_ul = False
    in_ol = False
    in_meta = False
    seen_h1 = False

    def close_lists() -> None:
        nonlocal in_ul, in_ol, in_meta
        if in_ul:
            out.append("</ul>")
            in_ul = False
        if in_ol:
            out.append("</ol>")
            in_ol = False
        if in_meta:
            out.append("</div>")
            in_meta = False

    for raw in lines:
        ln = raw.strip()
        if not ln:
            close_lists()
            continue
        if ln == "---":
            close_lists()
            continue
        if ln.startswith("# "):
            close_lists()
            seen_h1 = True
            out.append(
                '<div class="hero">'
                '<div class="kicker">PAYTM BUILD FOR INDIA AI HACKATHON | TRACK 1: MERCHANT GROWTH AI</div>'
                f"<h1>{inline_md(ln[2:].strip())}</h1>"
                "</div>"
            )
            continue
        if ln.startswith("## "):
            close_lists()
            out.append(f"<h2>{inline_md(ln[3:].strip())}</h2>")
            continue
        if ln.startswith("### "):
            close_lists()
            out.append(f"<h3>{inline_md(ln[4:].strip())}</h3>")
            continue
        if ln.startswith("- "):
            if in_ol:
                out.append("</ol>")
                in_ol = False
            # Top metadata block right after H1 before first H2
            if seen_h1 and not any(x.startswith("<h2>") for x in out):
                if not in_meta:
                    out.append('<div class="meta-card"><ul>')
                    in_meta = True
                    in_ul = True
                out.append(f"<li>{inline_md(ln[2:].strip())}</li>")
            else:
                if in_meta:
                    close_lists()
                if not in_ul:
                    out.append("<ul>")
                    in_ul = True
                out.append(f"<li>{inline_md(ln[2:].strip())}</li>")
            continue
        m_ol = re.match(r"^(\d+)\.\s+(.*)$", ln)
        if m_ol:
            if in_ul or in_meta:
                close_lists()
            if not in_ol:
                out.append("<ol>")
                in_ol = True
            out.append(f"<li>{inline_md(m_ol.group(2))}</li>")
            continue

        close_lists()
        out.append(f"<p>{inline_md(ln)}</p>")

    close_lists()
    return "\n".join(out)


def build_html(md_text: str) -> str:
    body = md_to_html_body(md_text)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>AI Tools, Runtime Models &amp; Safeguards Note - PaytmAI VyaparVoice</title>
<style>
  @page {{
    size: A4;
    margin: 14mm 15mm 15mm 15mm;
  }}
  * {{
    box-sizing: border-box;
  }}
  body {{
    margin: 0;
    font-family: "Calibri", "Carlito", "Liberation Sans", "Noto Sans", "Noto Sans Devanagari", "Noto Sans Kannada", sans-serif;
    font-size: 9.8pt;
    line-height: 1.42;
    color: #102038;
    background: #ffffff;
  }}
  .hero {{
    background: #002970;
    color: #ffffff;
    padding: 13px 16px 12px 16px;
    border-radius: 7px;
    border-top: 4px solid #00BAF2;
    margin-bottom: 10px;
  }}
  .kicker {{
    font-size: 7.8pt;
    font-weight: 700;
    letter-spacing: 0.5px;
    color: #7DD3FC;
    margin-bottom: 3px;
  }}
  h1 {{
    margin: 0;
    font-size: 16.5pt;
    font-weight: 700;
    color: #ffffff;
  }}
  .meta-card {{
    background: #F4F7FB;
    border: 1px solid #D5E0EE;
    border-left: 4px solid #0B5ED7;
    border-radius: 6px;
    padding: 8px 12px;
    margin-bottom: 11px;
  }}
  .meta-card ul {{
    margin: 0;
    padding-left: 16px;
  }}
  .meta-card li {{
    margin: 2px 0;
    font-size: 9.3pt;
  }}
  h2 {{
    margin: 12px 0 5px 0;
    padding-bottom: 3px;
    border-bottom: 1.5px solid #D5E0EE;
    font-size: 11.6pt;
    font-weight: 700;
    color: #002970;
    page-break-after: avoid;
    break-after: avoid;
  }}
  h3 {{
    margin: 8px 0 3px 0;
    font-size: 10.1pt;
    font-weight: 700;
    color: #0B5ED7;
    page-break-after: avoid;
    break-after: avoid;
  }}
  p {{
    margin: 4px 0 5px 0;
  }}
  ul, ol {{
    margin: 4px 0 7px 0;
    padding-left: 18px;
  }}
  li {{
    margin: 3.5px 0;
    page-break-inside: avoid;
    break-inside: avoid;
  }}
  strong {{
    color: #0B2545;
  }}
  code {{
    font-family: "Liberation Mono", "DejaVu Sans Mono", monospace;
    font-size: 8.6pt;
    background: #EEF3FA;
    color: #002970;
    padding: 1px 4px;
    border-radius: 3px;
  }}
</style>
</head>
<body>
{body}
</body>
</html>
"""


def main() -> None:
    md_text = MD_PATH.read_text(encoding="utf-8")
    violations = find_formatting_violations(md_text)
    if violations:
        raise ValueError(f"Formatting violations in {MD_PATH}: {violations}")

    html_doc = build_html(md_text)
    chromium_bin = shutil.which("chromium") or shutil.which("google-chrome")
    if not chromium_bin:
        raise RuntimeError("Chromium binary not found for PDF rendering")

    footer_tpl = (
        '<div style="width:100%;font-family:Calibri,Carlito,sans-serif;font-size:8pt;'
        'color:#4A5B73;padding:0 15mm;display:flex;justify-content:space-between;">'
        '<span>PaytmAI VyaparVoice | Team SemiTechnical (Kevin Joseph)</span>'
        '<span>AI Tools Note | Page <span class="pageNumber"></span> of <span class="totalPages"></span></span>'
        "</div>"
    )

    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=chromium_bin, args=["--no-sandbox", "--disable-gpu"])
        page = browser.new_page()
        page.set_content(html_doc, wait_until="load")
        page.pdf(
            path=str(PDF_PATH),
            format="A4",
            print_background=True,
            display_header_footer=True,
            header_template="<div></div>",
            footer_template=footer_tpl,
            margin={"top": "12mm", "bottom": "14mm", "left": "14mm", "right": "14mm"},
        )
        browser.close()

    print(f"Built {PDF_PATH} ({PDF_PATH.stat().st_size} bytes) from {MD_PATH.name} (0 formatting violations).")


if __name__ == "__main__":
    main()
