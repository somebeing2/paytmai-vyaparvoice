"""
Automated Stage Gate Preflight Checker (Task 17).
Verifies:
  1. .env is untracked and zero secret tokens appear in git-tracked files.
  2. render.yaml is unmodified relative to main.
  3. Zero em dashes (U+2014), zero en dashes (U+2013), and zero emojis in audited code/docs/HTML.
  4. Keyless Sarvam mock selftest passes.
  5. Stage 1 unit/concurrency suite, FastAPI E2E suite, and baseline 21/21 QA battery all pass.
"""
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.copy_lint import find_formatting_violations

SECRET_PATTERNS = [
    re.compile(r"gsk_[A-Za-z0-9]{20,}"),
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    re.compile(r"SARVAM_API_KEY[ \t]*=[ \t]*['\"]?[A-Za-z0-9_\-]{12,}"),
    re.compile(r"GROQ_API_KEY[ \t]*=[ \t]*['\"]?[A-Za-z0-9_\-]{12,}"),
]

HYGIENE_GLOBS = [
    "README.md",
    "AUDIT.md",
    "PLAN.md",
    "AGENT_HANDOFF.md",
    "results/slide_numbers.md",
    "results/unit_economics.md",
    "docs/SCRIPTS.md",
    "docs/QA_SHEET.md",
    "docs/COPY_REVIEW.md",
    "docs/TEACH_BACK.md",
    "docs/RUNBOOK.md",
    "config/*.yaml",
    "app/*.py",
    "app/providers/*.py",
    "app/static/*.html",
    "app/static/*.js",
    "scripts/*.py",
    "deck/v3/*.py",
]


def run_cmd(cmd: list[str], label: str) -> None:
    res = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    if res.returncode != 0:
        print(f"[FAIL] {label}\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}", file=sys.stderr)
        sys.exit(1)
    print(f"[PASS] {label}")


def check_git_and_secrets() -> None:
    tracked = subprocess.check_output(["git", "ls-files"], cwd=str(ROOT), text=True).splitlines()
    for rel in tracked:
        if rel == ".env" or rel.startswith(".env.") and rel != ".env.example":
            print(f"[FAIL] Secret env file is tracked by git: {rel}", file=sys.stderr)
            sys.exit(1)
        fp = ROOT / rel
        if not fp.is_file() or fp.suffix in (".pptx", ".pdf", ".png", ".jpg", ".wav", ".mp3"):
            continue
        txt = fp.read_text(encoding="utf-8", errors="ignore")
        for pat in SECRET_PATTERNS:
            if pat.search(txt):
                print(f"[FAIL] Potential secret key pattern matched in {rel}", file=sys.stderr)
                sys.exit(1)
    print("[PASS] Git tracked files clear of .env and secret key patterns")

    diff_render = subprocess.check_output(
        ["git", "diff", "main", "--", "render.yaml"], cwd=str(ROOT), text=True
    ).strip()
    if diff_render:
        print("[FAIL] render.yaml was modified without explicit approval!", file=sys.stderr)
        sys.exit(1)
    print("[PASS] render.yaml verified unmodified relative to main")


def check_formatting_hygiene() -> None:
    checked = 0
    for pattern in HYGIENE_GLOBS:
        for fp in sorted(ROOT.glob(pattern)):
            if not fp.is_file():
                continue
            txt = fp.read_text(encoding="utf-8")
            issues = find_formatting_violations(txt)
            if issues:
                rel = fp.relative_to(ROOT)
                print(f"[FAIL] Formatting violation in {rel}: {issues}", file=sys.stderr)
                sys.exit(1)
            checked += 1
    print(f"[PASS] Formatting hygiene verified across {checked} files (zero em/en dashes, zero emojis)")


def main() -> int:
    print("=== PaytmAI VyaparVoice Stage Gate Preflight ===\n")
    check_git_and_secrets()
    check_formatting_hygiene()
    run_cmd([sys.executable, "scripts/unit_economics.py"], "Task 8 reproducible unit economics report")
    run_cmd([sys.executable, "scripts/sarvam_cli.py", "selftest"], "Sarvam keyless mock selftest")
    run_cmd([sys.executable, "tests/test_stage1_unit.py"], "Stage 1 unit, power, ITT cap & concurrency tests")
    run_cmd([sys.executable, "tests/test_e2e_stage1.py"], "Stage 1 FastAPI E2E & visitor isolation tests")
    run_cmd([sys.executable, "tests/test_stage2.py"], "Stage 2 guardrails, cap editor, scorecard & unit-econ tests")
    run_cmd([sys.executable, "tests/test_groq_guardrails.py"], "Task 15 keyless Groq grounded Q&A, zero-PII & fallback tests")
    run_cmd([sys.executable, "tests/test_finals_7tasks.py"], "Finals 7-task keyless localisation, voice, alerts, cap & plain-language suite")
    run_cmd([sys.executable, "tests/qa_battery.py"], "Baseline 21/21 QA battery backwards-compatibility")
    print("\nALL PREFLIGHT CHECKS PASSED.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
