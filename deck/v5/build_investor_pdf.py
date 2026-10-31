#!/usr/bin/env python3
"""Render docs/INVESTOR_DEEP_DIVE.md into docs/INVESTOR_DEEP_DIVE.pdf.

Supports headings, metadata cards, nested unordered/ordered lists, markdown tables,
and inline bold/italic/code spans, verified with zero formatting violations.
"""

from __future__ import annotations

import html
import pathlib
import re
import shutil
import sys
from typing import List

from playwright.sync_api import sync_playwright

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.copy_lint import find_formatting_violations  # noqa: E402

MD_PATH = REPO_ROOT / "docs" / "INVESTOR_DEEP_DIVE.md"
PDF_PATH = REPO_ROOT / "docs" / "INVESTOR_DEEP_DIVE.pdf"


def inline_md(text: str) -> str:
    esc = html.escape(text, quote=False)
    code_tokens: List[str] = []

    def _save_code(m: re.Match) -> str:
        code_tokens.append(f"<code>{m.group(1)}</code>")
        return f"\x00CODE{len(code_tokens) - 1}\x00"

    esc = re.sub(r"`([^`]+)`", _save_code, esc)
    esc = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", esc)
    esc = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", esc)
    for idx, tok in enumerate(code_tokens):
        esc = esc.replace(f"\x00CODE{idx}\x00", tok)
    return esc


def parse_table(table_lines: List[str]) -> str:
    rows = []
    aligns: List[str] = []
    for idx, raw in enumerate(table_lines):
        cells = [c.strip() for c in raw.strip().strip("|").split("|")]
        if idx == 1 and all(re.match(r"^:?-{2,}:?$", c) for c in cells):
            for c in cells:
                if c.startswith(":") and c.endswith(":"):
                    aligns.append("center")
                elif c.endswith(":"):
                    aligns.append("right")
                else:
                    aligns.append("left")
            continue
        rows.append(cells)

    if not rows:
        return ""
    out = ['<div class="table-wrap"><table>']
    head = rows[0]
    out.append("<thead><tr>")
    for ci, cell in enumerate(head):
        al = aligns[ci] if ci < len(aligns) else "left"
        out.append(f'<th style="text-align:{al};">{inline_md(cell)}</th>')
    out.append("</tr></thead><tbody>")
    for r in rows[1:]:
        out.append("<tr>")
        for ci, cell in enumerate(r):
            al = aligns[ci] if ci < len(aligns) else "left"
            out.append(f'<td style="text-align:{al};">{inline_md(cell)}</td>')
        out.append("</tr>")
    out.append("</tbody></table></div>")
    return "\n".join(out)


def md_to_html_body(md_text: str) -> str:
    lines = md_text.splitlines()
    out: List[str] = []
    in_ul = False
    in_sub_ul = False
    in_ol = False
    in_meta = False
    seen_h1 = False
    seen_h2 = False
    table_buf: List[str] = []

    def flush_table() -> None:
        nonlocal table_buf
        if table_buf:
            out.append(parse_table(table_buf))
            table_buf = []

    def close_lists() -> None:
        nonlocal in_ul, in_sub_ul, in_ol, in_meta
        if in_sub_ul:
            out.append("</ul></li>")
            in_sub_ul = False
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
        s = raw.strip()
        if s.startswith("|") and s.endswith("|"):
            close_lists()
            table_buf.append(s)
            continue
        else:
            flush_table()

        if not s or s == "---":
            close_lists()
            continue

        if s.startswith("# "):
            close_lists()
            seen_h1 = True
            out.append(
                '<div class="hero">'
                '<div class="kicker">INVESTOR, TECHNICAL &amp; UNIT-ECONOMICS DILIGENCE BRIEFING | TRACK 1: MERCHANT GROWTH AI</div>'
                f"<h1>{inline_md(s[2:].strip())}</h1>"
                "</div>"
            )
            continue
        if s.startswith("## "):
            close_lists()
            seen_h2 = True
            sec_title = s[3:].strip()
            cls = ' class="page-section"' if sec_title.startswith("10.") else ""
            out.append(f"<h2{cls}>{inline_md(sec_title)}</h2>")
            continue
        if s.startswith("### "):
            close_lists()
            out.append(f"<h3>{inline_md(s[4:].strip())}</h3>")
            continue

        # Indented sub-bullet under ordered or unordered list
        if raw.startswith("   - ") or raw.startswith("  - "):
            item_txt = s[2:].strip()
            if not in_sub_ul:
                # Attach sub-list inside previous <li> if possible
                if out and out[-1].endswith("</li>"):
                    out[-1] = out[-1][:-5]
                    out.append('<ul class="sub-list">')
                    in_sub_ul = True
                else:
                    if not in_ul:
                        out.append("<ul>")
                        in_ul = True
            out.append(f"<li>{inline_md(item_txt)}</li>")
            continue

        if in_sub_ul:
            out.append("</ul></li>")
            in_sub_ul = False

        if s.startswith("- "):
            if in_ol:
                out.append("</ol>")
                in_ol = False
            if seen_h1 and not seen_h2:
                if not in_meta:
                    out.append('<div class="meta-card"><ul>')
                    in_meta = True
                    in_ul = True
                out.append(f"<li>{inline_md(s[2:].strip())}</li>")
            else:
                if in_meta:
                    close_lists()
                if not in_ul:
                    out.append("<ul>")
                    in_ul = True
                out.append(f"<li>{inline_md(s[2:].strip())}</li>")
            continue

        m_ol = re.match(r"^(\d+)\.\s+(.*)$", s)
        if m_ol:
            if in_ul or in_meta:
                close_lists()
            if not in_ol:
                out.append("<ol>")
                in_ol = True
            out.append(f"<li>{inline_md(m_ol.group(2))}</li>")
            continue

        close_lists()
        out.append(f"<p>{inline_md(s)}</p>")

    flush_table()
    close_lists()
    return "\n".join(out)


def build_html(md_text: str) -> str:
    body = md_to_html_body(md_text)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>PaytmAI VyaparVoice - Investor, Technical &amp; Economics Deep-Dive</title>
<style>
  @page {{
    size: A4;
    margin: 13mm 14mm 15mm 14mm;
  }}
  * {{
    box-sizing: border-box;
  }}
  body {{
    margin: 0;
    font-family: "Calibri", "Carlito", "Liberation Sans", "Noto Sans", "Noto Sans Devanagari", "Noto Sans Kannada", sans-serif;
    font-size: 9.5pt;
    line-height: 1.42;
    color: #102038;
    background: #ffffff;
  }}
  .hero {{
    background: linear-gradient(135deg, #001B4D 0%, #002970 100%);
    color: #ffffff;
    padding: 14px 18px 13px 18px;
    border-radius: 7px;
    border-top: 4px solid #00BAF2;
    margin-bottom: 10px;
  }}
  .kicker {{
    font-size: 7.6pt;
    font-weight: 700;
    letter-spacing: 0.5px;
    color: #7DD3FC;
    margin-bottom: 4px;
  }}
  h1 {{
    margin: 0;
    font-size: 16pt;
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
    margin: 2.5px 0;
    font-size: 9.1pt;
  }}
  h2 {{
    margin: 13px 0 6px 0;
    padding: 4px 8px;
    background: #EEF4FC;
    border-left: 4px solid #002970;
    border-radius: 0 4px 4px 0;
    font-size: 11.4pt;
    font-weight: 700;
    color: #002970;
    page-break-after: avoid;
    break-after: avoid;
  }}
  h2.page-section {{
    page-break-before: always;
    break-before: page;
  }}
  h3 {{
    margin: 9px 0 4px 0;
    font-size: 10.0pt;
    font-weight: 700;
    color: #0B5ED7;
    page-break-after: avoid;
    break-after: avoid;
  }}
  p {{
    margin: 4px 0 6px 0;
  }}
  ul, ol {{
    margin: 4px 0 7px 0;
    padding-left: 18px;
  }}
  ul.sub-list {{
    margin: 3px 0 3px 0;
    padding-left: 16px;
  }}
  li {{
    margin: 3.5px 0;
  }}
  strong {{
    color: #0B2545;
  }}
  code {{
    font-family: "Liberation Mono", "DejaVu Sans Mono", monospace;
    font-size: 8.3pt;
    background: #EEF3FA;
    color: #002970;
    padding: 1px 4px;
    border-radius: 3px;
  }}
  .table-wrap {{
    margin: 7px 0 10px 0;
    page-break-inside: avoid;
    break-inside: avoid;
  }}
  table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 8.6pt;
    line-height: 1.32;
  }}
  th {{
    background: #002970;
    color: #ffffff;
    font-weight: 700;
    padding: 5px 7px;
    border: 1px solid #002970;
  }}
  th code {{
    background: rgba(255, 255, 255, 0.2);
    color: #ffffff;
  }}
  td {{
    padding: 5px 7px;
    border: 1px solid #D5E0EE;
    vertical-align: top;
  }}
  tbody tr:nth-child(even) td {{
    background: #F8FAFD;
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
        '<div style="width:100%;font-family:Calibri,Carlito,sans-serif;font-size:7.8pt;'
        'color:#4A5B73;padding:0 14mm;display:flex;justify-content:space-between;">'
        '<span>PaytmAI VyaparVoice | Team SemiTechnical (Kevin Joseph) | Investor &amp; Technical Deep-Dive</span>'
        '<span>Page <span class="pageNumber"></span> of <span class="totalPages"></span></span>'
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
