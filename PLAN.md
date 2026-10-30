# Execution Plan and Reconciled Consolidated Prompt Schedule (PLAN.md)

Date: 30 October 2026
Time Budget: 5 hours to Feature Freeze
Repository: `https://github.com/somebeing2/paytmai-vyaparvoice` (branch `main`)
Live Demo URL: `https://paytmai-vyaparvoice.onrender.com`

---

## 1. Non-Negotiable Engineering, Deployment, and Editorial Rules

1. **Zero Spend / Keyless Repo:** Only free tiers and open-source packages. Zero API keys in code, configs, tests, or logs. All external providers read credentials solely from local `.env` and fail closed on missing keys, disabled flags, or quota/HTTP errors.
2. **Branch-First Deployment Safety (`render.yaml` Untouched):** `render.yaml` remains unmodified. All development runs on feature branches (`work/*`). Documentation-only commits carry `[skip render]`. Merge to local `main` and tag (`stage1-ok`, `stage2-ok`, `release-final`) only when `make preflight` and all test suites pass.
3. **Intention-to-Treat (ITT) Cap-vs-Holdout Accounting:** Issue passes to every nudged customer (`32` passes = `Rs 800` face exposure vs `Rs 300` hard spend stop on `CMP-WINBACK-01`; pass terms state `valid while shop offer budget lasts`). Simulator draws outcomes independently of the cap first, then applies the atomic spend stop (`cap_reached`, `refused_redemptions`), analysing holdout lift strictly as **Intention-to-Treat (ITT)**. Approval warns when `P(overrun) > 10%` and suggests a higher cap.
4. **Pooled 50-Shop Stratified Pilot & Power Discipline:** Never claim a single shop yields 4 full waves in 4 weeks (which conflicts with the 14-day cooldown and `~0.78` steady-state waves/month). Instead, design the pilot as **50 shops x 1 wave (`~40` eligible/shop = `~400` control + `~1,600` nudged), randomized within each shop, stratified by shop** (`50.3%`, `68.8%`, `83.3%`, `92.5%`, `97.2%`, `99.8%` power at `+4, +5, +6, +7, +8, +10 pp` lift above `12.5%` baseline). Pilot advances **only if the lower 95% bound of post-5%-fee net profit per nudged customer > Rs 0 AND observed lift > break-even lift (`+15.3 pp` post-fee at `30%` margin)**.
5. **Paytm Q2 FY27 Primary Attribution, Copy Status & Fee Reconciliation:** Use `Reported (Paytm Q2 FY27 release, 26 Oct 2026)` with primary `ir.paytm.com` / `paytm.com` URLs (`1.64 Cr` subscription merchants, `Rs 7.1L Cr` GMV, `Rs 2,648 Cr` revenue). Label `~7%` merchant loan penetration and `Rs 90-100/mo` Soundbox rental as `ASSUMPTION`. Mark English copy `EN author-checked, native review pending` and KN/HI `DRAFT - UNREVIEWED BY NATIVE SPEAKER`. Reconcile `Rs 130.50` single-wave `5%` fee (all redeemed bills including organic returners) with `Rs 102/mo` steady-state ARPU (`~0.78` waves/mo).
6. **Formatting & Render Bounds:** Zero em/en dashes and zero emojis. Per-visitor Render session DBs enforce TTL (`1,800s`), max active sessions (`64`, evict oldest), per-DB cap (`2 MB`), and total session disk cap (`32 MB`).

---

## 2. Reconciled Task Map & Exact Stage Order

| Stage / Task | Scope & Deliverables | Branch / Gate |
| :--- | :--- | :--- |
| **Step 0 & Deck v1** | Forensic audit (`AUDIT.md`), canonical ledger (`results/slide_numbers.md`), `deck/original/`, `deck/v1/`, `docs/SCRIPTS.md`, `docs/QA_SHEET.md`, `docs/COPY_REVIEW.md` | `work/step0-and-deck-v1` [DONE] |
| **Stage 1 (P0): Tasks 6, 5, 7, 14, 4, 17** | Config (`app/config.py`), Render session TTL/count/size bounds & `ADMIN_TOKEN` (`app/sessions.py`, `app/security.py`), keyless Sarvam + mock server + `15%/15%/30%` caps (`app/providers/`, `app/ledger.py`), copy linter & templates (`app/copy_lint.py`, `app/templates.py`), ITT stats/cap/concurrency engine (`app/stats.py`, `app/engine.py`), `Makefile`, `docs/RUNBOOK.md`, unit & E2E tests | `main` (`stage1-ok`) [DONE] |
| **Deck v2.1 (`[skip render]`)** | Pooled 50-shop pilot power (`400C + 1,600T`), new A9 decision rule, `EN author-checked, native review pending`, `[BUILT]` tags + plain capability tiles + ITT definition on Main Slide 4, clean A2 disclosures, Q4 cap-refusal answer | `work/deck-v2` [DONE] |
| **Stage 2 - P1.1: Confirm/Complete Task 4 & Task 14 Gaps** | Task 4: interactive guardrail attack (`"Type your own attack"`), What-If parameter panel, judge-speaks mic flow with button fallback. Task 14: merchant question chips, `Repeat` and `Slower` controls, `"Why?"` explanation button, complete teach-back doc (`docs/TEACH_BACK.md`) | `main` (`stage2-ok`) [DONE] |
| **Stage 2 - P1.2: Task 9 (Cap Editor, Live Interim Dashboard & Break-Even)** | Cap editor (presets, two-step voice cap change with confirmation, bounds check, audit log), live campaign dashboard with interim directional labels & atomic stop-loss control, interactive break-even calculator | `main` (`stage2-ok`) [DONE] |
| **Stage 2 - P1.3: Task 11 (Merchant Scorecard)** | Plain-language verdict, conjugate `Beta(1,1)` Bayesian probability of positive net profit, 4-stage visual evidence meter, `6x4` margin/fee sensitivity table, Evidence Grades `A/B/C` | `main` (`stage2-ok`) [DONE] |
| **Stage 2 - P1.4: Task 8 (Unit-Economics Script & Report)** | Reproducible `scripts/unit_economics.py` and generated `results/unit_economics.md` reconciling SaaS, promo fee, credit sensitivity, and Bulbul TTS caching | `main` (`stage2-ok`) [DONE] |
| **Deck v3 (`[skip render]`)** | Rebuilt 18-slide presentation (`deck/v3/PaytmAI_VyaparVoice_v3.pptx` & `.pdf`) adding `A12` (Cap Editor & Stop-Loss) and `A13` (Bayesian Scorecard & `6x4` Margin-Fee Matrix) traced to `results/slide_numbers.md` and `results/unit_economics.md` | `work/deck-v3` -> `main` [DONE] |
| **Stage 2 - P1.5: Task 15 (Optional Keyless Groq Layer)** | Executed after `stage2-ok`: keyless Groq free-tier English grounded Q&A (`app/providers/groq_qa.py`, `tests/test_groq_guardrails.py`), `PUBLIC_DEPLOY=true` hard-blocked, zero PII outbound, SQLite number & copy-lint gates | `work/stage2-groq` -> `main` [DONE] |
| **Stage 3 - P1.6: Task 17c (Offline Replay & Handoff)** | Zero-network static fallback (`app/static/demo_replay.html` & `/replay`), `AGENT_HANDOFF.md`, `make preflight` + `make export`, final tags `stage3-ok` & `release-final` | `main` (`release-final`) [DONE] |
