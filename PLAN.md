# Execution Plan and Stage Gate Schedule (PLAN.md)

Date: 30 October 2026
Time Budget: 5 hours to Feature Freeze
Repository: `https://github.com/somebeing2/paytmai-vyaparvoice` (branch `main`)
Live URL: `https://paytmai-vyaparvoice.onrender.com`

---

## 1. Non-Negotiable Engineering and Editorial Rules
1. **Zero Spend / Keyless Repo:** Only free tiers and open-source packages. No API keys in code, configs, tests, or logs. All external adapters read keys solely from local `.env` and fail closed on missing keys or quota errors.
2. **Branch-First Deployment Safety:** Because Render auto-deploys every push to `main`, all implementation runs on feature branches (`work/*`). Merge to local `main` and tag (`stage1-ok`, `stage2-ok`, `stage3-ok`, `release-final`) only when `make preflight` and the full test battery pass. Export via `make export` for controlled local push.
3. **Statistical and Financial Honesty:** Every number on slides or UI traces to `results/slide_numbers.md` or `AUDIT.md`. All synthetic data, simulated redemptions, assumptions, pilot targets, and pending sponsor integrations are explicitly labelled.
4. **Formatting:** Formal, concise prose. Zero em dashes (`\u2014`) and zero emojis across all code comments, UI copy, markdown docs, and slides.

---

## 2. Staged Execution Sequence (Per Amendments Section 4)

### Step 0: Baseline Audit and Ledger (Hour 0.0 - 0.5) [COMPLETE]
- Inspect Python runtime, `render.yaml`, Render `autoDeploy` specification, and Git state.
- Back up untouched Round 1 presentation files to `deck/original/`.
- Produce `AUDIT.md`, `results/slide_numbers.md`, and `PLAN.md`.

### Deck v1 + Pitch Documentation (Hour 0.5 - 1.5) [IN PROGRESS]
- Build `deck/v1/PaytmAI_VyaparVoice_v1.pptx` and `.pdf` from `AUDIT.md` and `results/slide_numbers.md`:
  - **Slides 1-5 (Lean Main Deck, >=18 pt body text, <=5 bullets/slide, full speaker notes):**
    1. Problem (dated Paytm Q1 FY27 / Q4 FY26 citations; assumptions labelled).
    2. Solution and Live Demo Moment (synthetic dataset explicitly disclosed).
    3. How It Works (`Built in MVP` vs `Production Plan` vs `Pending Sponsor Window` tags; zero unverified Sarvam claims).
    4. Simulated Holdout Proof & Honest Statistics (`12/32` vs `1/8`, Fisher `p = 0.24`, Wilson 95% CIs, `n = 46/arm` power requirement, `5.8x` labelled as gross sales multiple alongside `30%`-margin `+Rs 222` net profit / `1.74x` gross-profit multiple).
    5. Business Model (3 revenue cases: `Rs 74.4 Cr`, `Rs 170.5 Cr`, `Rs 243.0 Cr`; consistent `Rs 5` cached vs `Rs 28.80` uncached AI cost and `81.4%` vs `72.2%` margin) and Bengaluru Pilot Validation Plan.
  - **Slides 6-14 (Corrected Appendix):** Corrected versions of original slides with all inconsistencies, labels, and speaker notes fixed.
  - Visually render every slide to PNG and inspect 100% of slides for overflow, overlap, contrast, and banned characters.
- Produce `docs/SCRIPTS.md` (60s, 3m, 5m, and 7m timed scripts, with live-demo vs deck-only variants), `docs/QA_SHEET.md` (15 hardest questions with defensible answers), and `docs/COPY_REVIEW.md` (merchant English, Kannada, and Hindi strings for native review + teach-back protocol).

### Stage 1: Honest Statistics, Commitment Cap, Copy Linter & Public Safeguards (Hour 1.5 - 2.75)
- **Honest Stats Engine (`app/stats.py`):** Exact Fisher test, Wilson 95% CIs, two-proportion power calculator, profit-based ROI (`gross_profit`, `net_profit_pre_fee`, `net_profit_post_fee`, `organic_subsidy_inr`, `breakeven_margin_pct`), interim suppression of significance claims, and randomized dose-response budget-return simulation.
- **Commitment-Based Cashback Cap Ledger (`app/ledger.py`):** Separate merchant promo cap from Sarvam credit ledger; count issued-but-unredeemed passes as committed liability (wave-capped at `12` active passes for `Rs 300` cap, or explicit commitment warning).
- **Merchant Communication & Copy Linter (`app/templates.py`, `tests/test_copy_lint.py`):** Deterministic string templates (zero LLM-written numbers), short sentences, banned-jargon glossary (`RFM`, `cohort`, `holdout`, `p-value`, etc. banned in Merchant View; shown only in Technical View), evidence grades `A/B/C`, Kannada/Hindi marked `UNREVIEWED DRAFT` until native sign-off.
- **Public Deploy Safeguards:** `PUBLIC_DEPLOY=true` mode, `ADMIN_TOKEN` header protection for global mutations, per-session isolated demo state so concurrent visitors on Render do not clobber each other.
- **Gate:** `make preflight` + full pytest/QA suite -> merge to `main` -> tag `stage1-ok`.

### Stage 2: Keyless Sarvam & Groq Adapters, Cached Audio & Makefile Workflow (Hour 2.75 - 4.0)
- **Sarvam Keyless Adapter (`config/sarvam.yaml`, `app/adapters/sarvam.py`):**
  - Dual feature flags (`SARVAM_ENABLED=false`, `SARVAM_LIVE_CALLS_ENABLED=false` by default; strictly disabled when `PUBLIC_DEPLOY=true`).
  - Credit ledger tracking universal balance with hard `15%` cap per capability (`30%` combined cap) and fail-closed behavior on any HTTP/billing error.
  - Mock-server unit tests verifying Bulbul TTS and Saarika ASR payloads without live keys.
  - Targets: `make ledger-set-balance`, `make sarvam-selftest`, `make activate-sarvam` (regenerates local cached `.wav/.mp3` briefings for deterministic offline playback).
- **Groq Keyless Adapter (`app/adapters/groq_qa.py`):**
  - Grounded English-only store Q&A, intent fallback, and prompt-injection / discount-attack validator ("Type your own attack" guardrail test proving LLM cannot alter `offer_rupees` or `max_budget`); zero PII sent; graceful offline fallback when `GROQ_API_KEY` is unset.
- **Results Regeneration:** Export verified simulated metrics to `results/slide_numbers.md`.
- **Gate:** `make preflight` + mock-server tests -> merge to `main` -> tag `stage2-ok`.

### Deck v2: Scorecard and Spending-Cap / Break-Even Update (Hour 4.0 - 4.5)
- Generate `deck/v2/PaytmAI_VyaparVoice_v2.pptx` and `.pdf`:
  - Add the **Merchant Scorecard Slide** (Merchant View vs Technical View, Evidence Grades A/B/C) and **Spending Cap & Profit Break-Even Slide** (commitment cap vs Sarvam credit cap, dose-response curve, break-even margin math), strictly sourced from `results/slide_numbers.md` and labelled `SIMULATED`.
  - Render all slides to PNG and inspect visually.

### Stage 3: Offline Demo Hardening, Static Replay, Runbook & Final Freeze (Hour 4.5 - 5.0)
- Build standalone `static_replay.html` (zero-backend emergency fallback replay).
- Write `docs/RUNBOOK.md` (1-page venue checklist: `127.0.0.1` usage, Render 2-minute warm-up, phone hotspot, Saturday 11 AM Sarvam activation checklist) and `AGENT_HANDOFF.md`.
- Run full end-to-end scripted test + `make preflight` + `make export`.
- Merge to `main`, tag `stage3-ok` and `release-final`. Feature freeze at Hour 5.0.
