# Execution Plan and Reconciled Consolidated Prompt Schedule (PLAN.md)

Date: 30 October 2026
Time Budget: 5 hours to Feature Freeze
Repository: `https://github.com/somebeing2/paytmai-vyaparvoice` (branch `main`)
Live Demo URL: `https://paytmai-vyaparvoice.onrender.com`

---

## 1. Non-Negotiable Engineering, Deployment, and Editorial Rules

1. **Zero Spend / Keyless Repo:** Only free tiers and open-source packages. Zero API keys in code, configs, tests, or logs. All external providers read credentials solely from local `.env` and fail closed on missing keys, disabled flags, or quota/HTTP errors.
2. **Branch-First Deployment Safety (`render.yaml` Untouched):** `render.yaml` remains unmodified. All development runs on feature branches (`work/*`). Documentation-only commits carry `[skip render]` in the commit message. Merge to local `main` and tag (`stage1-ok`, `stage2-ok`, `stage3-ok`, `release-final`) only when `make preflight` and all test suites pass.
3. **Intention-to-Treat (ITT) Cap-vs-Holdout Accounting (Decision 1):** Issue passes to every nudged customer (`32` passes = `Rs 800` face exposure vs `Rs 300` hard spend ceiling on `CMP-WINBACK-01`). Treat the rupee cap strictly as a hard stop on actual cashback spend (`actual_spend <= max_budget`), recording `cap_reached` and `refused_redemptions`. Simulator draws customer return outcomes independently of the cap first, then applies the spend stop, and analyses holdout lift strictly as **Intention-to-Treat (ITT)** so the causal holdout comparison is unchanged when the cap binds. At approval, compute binomial probability of exceeding the cap under the assumed redemption rate and warn when `> 10%` with a suggested higher cap.
4. **Statistical Power & Allocation Honesty (Decision 2):** Power calculator supports `allocation_ratio = n_treatment / n_control`: at `80/20` allocation (`r = 4.0`, `40` eligible per wave) for `12.5%` vs `37.5%` (`alpha = 0.05` two-sided, `80%` power), required sample is `31` control and `124` nudged (`155` total, roughly `4` waves), versus `46` per arm (`92` total) at a `50/50` (`r = 1.0`) even split.
5. **Paytm Q2 FY27 Primary Attribution & Fee Reconciliation (Decisions 3 & 4):** Use `Reported (Paytm Q2 FY27 release, 26 Oct 2026)` with primary `ir.paytm.com` / `paytm.com` URLs (`1.64 Cr` subscription-paying merchants, `Rs 7.1L Cr` GMV, `Rs 2,648 Cr` operating revenue). Label `~7%` merchant loan penetration and `Rs 90 to 100/mo` Soundbox rental as `ASSUMPTION` (with historical FY24/FY25 Paytm IR benchmark notes). Reconcile `Rs 130.50` single-campaign `5%` fee (levied on all `Rs 2,610` redeemed bills including organic returners) with the `Rs 102/mo` steady-state monthly assumption (`~0.78` win-back-equivalent campaigns/month = `Rs 2,040/mo` redeemed promo bills).
6. **Formatting & Deck Hygiene (Decision 5):** Formal, concise prose. Zero em dashes (`\u2014`), zero en dashes (`\u2013`), and zero emojis in docs, templates, and slides. Deck v2 uses real bullets instead of literal asterisks, fills/resizes cards on Slides 4 and 5, and adds `https://paytmai-vyaparvoice.onrender.com` + QR code to Slide 2.

---

## 2. Reconciled Task Map (Consolidated Prompt Tasks Mapped to Stages)

| Consolidated Prompt Task | Scope & Deliverables | Target Branch / Gate |
| :--- | :--- | :--- |
| **Step 0: Forensic Audit & Ledger** | Runtime check, `render.yaml` evaluation, `deck/original/` archive, `AUDIT.md`, `results/slide_numbers.md`, `PLAN.md` | `work/step0-and-deck-v1` [DONE] |
| **Deck v1 + Pitch Docs** | Lean 5-slide main deck + 9-slide appendix (`deck/v1/`), `docs/SCRIPTS.md`, `docs/QA_SHEET.md`, `docs/COPY_REVIEW.md` | `work/step0-and-deck-v1` [DONE] |
| **P0.1 - Task 6: Config Layer** | `app/config.py`, `config/default.yaml`, `config/sarvam.yaml`, updated `.env.example` (env + YAML typed config, zero secrets, margin/fee/allocation/cap-warning settings) | `work/stage1-core` (`stage1-ok`) |
| **P0.2 - Task 5: Reliability & Render Safeguards** | `app/sessions.py`, `app/security.py`, `app/main.py`: `PUBLIC_DEPLOY=true` paid-call lock, `ADMIN_TOKEN` header gate for global mutations, per-visitor isolated SQLite sessions (`X-Demo-Session` / cookie + TTL cleanup), `/api/health` readiness metadata | `work/stage1-core` (`stage1-ok`) |
| **P0.3 - Task 7: Provider Layer & Keyless Sarvam** | `app/providers/` (`base.py`, `sarvam.py`, `webspeech.py`, `cache.py`), `app/ledger.py`, `tests/mock_sarvam_server.py`, `scripts/sarvam_cli.py`: keyless Bulbul TTS + Saaras/Saarika STT + Translate adapter, `15%` TTS / `15%` STT (`30%` combined) universal credit cap, fail-closed billing handling, phrase-hash audio cache, `make ledger-set-balance`, `make sarvam-selftest`, `make activate-sarvam` | `work/stage1-core` (`stage1-ok`) |
| **P0.4 - Task 14: Merchant Communication Layer** | `app/templates.py`, `app/copy_lint.py`, `tests/test_copy_lint.py`, `docs/COPY_REVIEW.md`: deterministic templates (zero LLM numbers), Merchant View vs Technical View separation, banned-jargon & banned-char linter, Evidence Grades `A/B/C`, `[DRAFT - UNREVIEWED]` tags on `kn-IN` / `hi-IN` | `work/stage1-core` (`stage1-ok`) |
| **P0.5 - Task 4: Demo Moments & Honest Stats / ITT Cap Engine** | `app/stats.py`, `app/engine.py`, `app/database.py`, `app/static/index.html`: Fisher exact p, Wilson 95% CIs, `allocation_ratio` power calculator (`31/124` at `80/20`, `46/46` at `50/50`), profit-based ROI + fee reconciliation, ITT cap-vs-holdout (`32` passes issued, hard spend stop, `cap_reached`, `refused_redemptions`, `>10%` cap-binding probability warning + suggested cap, atomic concurrency lock), randomized dose-response simulator, Merchant/Technical UI toggle | `work/stage1-core` (`stage1-ok`) |
| **P0.6 - Task 17: Preflight, Runbook & End-to-End Test** | `Makefile`, `scripts/preflight.py`, `docs/RUNBOOK.md`, `tests/test_stage1_unit.py`, `tests/test_e2e_stage1.py`, backwards-compatible `tests/qa_battery.py` (`21/21`) | `work/stage1-core` (`stage1-ok`) |
| **P1 - Stage 2: Optional Groq Grounded Q&A & Security Demo** | `app/providers/groq_qa.py`, `tests/test_groq_guardrails.py`: keyless Groq English-only grounded store Q&A, intent fallback, interactive prompt-injection / discount-attack validator (`"Type your own attack"` proving `offer_rupees` and `max_budget` cannot be altered; zero PII sent), automated `results/slide_numbers.md` export | `work/stage2-optional` (`stage2-ok`) |
| **Deck v2: Updated Q2 FY27, ITT Cap, Power, Cosmetic & Scorecard Slides** | `deck/v2/PaytmAI_VyaparVoice_v2.pptx` & `.pdf`: applies Decisions 1-5 (ITT cap trade-off + `simulated 12 = cap`, `80/20` power `31/124`, Paytm Q2 FY27 `1.64 Cr` / `Rs 2,648 Cr`, `Rs 102` vs `Rs 130.50` fee reconciliation, real PPTX bullets, resized Slide 4/5 cards, Slide 2 live URL + QR code, Merchant Scorecard + Cap/Break-Even slide) | `work/deck-v2` |
| **P2 - Stage 3: Static Offline Replay, Handoff & Final Freeze** | `app/static/demo_replay.html` (zero-backend fallback), `AGENT_HANDOFF.md`, full `make preflight` + `make export`, final merge & tags (`stage3-ok`, `release-final`) | `work/stage3-freeze` (`release-final`) |

---

## 3. Stage 1 Acceptance Checklist (`work/stage1-core` -> `stage1-ok`)

1. `Task 6`: `app/config.py` loads `config/default.yaml` + `config/sarvam.yaml` + env overrides with zero secrets.
2. `Task 5`: `PUBLIC_DEPLOY=true` blocks live paid calls; global admin routes require `X-Admin-Token`; concurrent demo visitors receive isolated SQLite session databases so resets/approvals never collide.
3. `Task 7`: Mock Sarvam HTTP server test verifies Bulbul TTS and Saaras/Saarika STT headers/payloads, `15%/15%` (`30%` total) credit cap enforcement, fail-closed behavior on `402/429/500`, cached audio hit bypass, and `make sarvam-selftest`.
4. `Task 14`: Merchant View passes automated banned-jargon (`cohort`, `holdout`, `p-value`, `ROI`, `DPDP`, etc.) and zero-em-dash/zero-emoji lint; `kn-IN` and `hi-IN` carry `[DRAFT - UNREVIEWED]`; Evidence Grades `A/B/C` attached to all claims.
5. `Task 4`:
   - Power calculator verified against reference values (`46` per arm at `1:1`; `31` control / `124` nudged = `155` total at `4:1` `80/20`).
   - Cap-vs-holdout verified: `32` passes issued (`Rs 800` face exposure vs `Rs 300` hard spend stop); approval warns when `P(overrun) > 10%` and suggests higher cap; simulator draws return outcomes independently of cap and then truncates funded payouts, setting `cap_reached` and `refused_redemptions`; test proves ITT holdout comparison (`itt_returners/32` vs `holdout_returners/8`, Fisher `p`, Wilson CIs) is **unchanged** when cap binds; multi-threaded concurrency test proves `budget_spent` never exceeds `max_budget`.
6. `Task 17`: `make preflight` runs secret scan, tracked-`.env` check, banned-character scan, copy-jargon lint, mock Sarvam selftest, unit/concurrency/E2E tests, and `tests/qa_battery.py` (`21/21`), all exiting `0` before merging `work/stage1-core` to `main` and tagging `stage1-ok`.
