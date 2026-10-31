# PaytmAI VyaparVoice - Engineering Portfolio Case Study (v1.8)

**Project:** PaytmAI VyaparVoice (Merchant Growth AI Copilot)
**Author:** Kevin Joseph (Team SemiTechnical)
**Stack:** Python 3.11, FastAPI, SQLite (WAL + `BEGIN IMMEDIATE` atomic locking), Sarvam AI (`sarvam-105b-conversations`, `saaras:v4`, `bulbul:v3` / `bulbul:v4-flash`), Groq (`openai/gpt-oss-20b`, `whisper-large-v3-turbo`), Vanilla JS (`EN` / `KN` / `HI` i18n), Docker

---

## 1. Problem Statement & Core Architectural Thesis

Neighbourhood merchants accepting UPI QR payments generate hundreds of repeat transactions each month, yet lack three practical capabilities at closing time:
1. Identifying which regular customers have quietly stopped visiting or when afternoon traffic drops.
2. Sending bounded promotional offers without risking uncapped discount spend or spamming unconsented customers.
3. Measuring whether returning buyers came because of the offer or would have visited organically anyway.

**Core Engineering Principle:** Language and speech models handle multilingual communication (Kannada, Hindi, English), intent parsing, and natural Q&A, while **100% of financial math, budget caps, minimum-bill checks, DPDP consent filtering, and holdout attribution execute inside deterministic Python + atomic SQLite transactions**. An LLM prompt injection can never mint an unapproved discount or exceed the merchant's rupee budget cap.

*Hardware & Platform Validation Note:* To our knowledge the standard Paytm Soundbox is speaker-based with no microphone; this is to be validated with Paytm. Two-way voice commands run via the Paytm for Business companion mobile app microphone or future mic-capable hardware, while spoken briefings play on the Soundbox speaker or phone. Per-customer payer identifiers in real Paytm QR ledgers, customer WhatsApp/push notification delivery, shop gross margins (`30%` Darshini default), promotional fee rates (`5%`), and SaaS pricing (`Rs 79/mo`) are treated as explicit, configurable assumptions (`Grade C`).

---

## 2. System Architecture & Key Modules

| Layer | Module | Engineering Responsibility |
| :--- | :--- | :--- |
| **Atomic Ledger & Causal Engine** | `app/engine.py`, `app/database.py` | RFM customer segmentation, 14-day cooldown & DPDP consent filtering, deterministic `80/20` stratified holdout split (`SHA-256` seeded), `BEGIN IMMEDIATE` pass redemption (`redeem_single_pass_atomic`), Intent-to-Treat (ITT) lift, Fisher exact & Wilson 95% CIs, and `50% / 80% / 100%` threshold alerts. |
| **Zero-PII CSV Ingest & Store Presets** | `app/csv_ingest.py` | Adapts margin economics across `Darshini / Cafe (30%)`, `Grocery Kirana (18%)`, and `Bakery / Sweet Shop (35%)`. Parses real merchant UPI CSV exports, `SHA-256` hashes raw payer IDs/phones in memory before SQLite insert, recomputes RFM cohorts, and rebuilds holdout campaigns automatically. |
| **Customer QR Pass Wallet & Counter Scanner** | `app/pass_wallet.py` | Issues auditable `PASS-...` tokens for the `32` treatment buyers while holding `8` control buyers unmessaged; enforces `min_bill` and hard rupee caps at counter scan time; renders DPDP-compliant (`STOP` opt-out) WhatsApp previews with optional PIN-locked Twilio Sandbox dispatch. |
| **Multi-Shop Pooled Pilot Simulator** | `app/pass_wallet.py` (`simulate_multi_shop_pilot`) | Models `1..200` participating shops across `1..12` waves to demonstrate why a single `40`-buyer shop wave is directional (`p = 0.2364`, low power) whereas a `50`-shop (`2,000`-buyer) pooled holdout pilot achieves `>80%` statistical power for a `+7 pp` true lift. |
| **Multilingual Voice & LLM Stack** | `app/providers/sarvam.py`, `app/providers/groq_qa.py` | Primary Indian-language TTS (`bulbul:v3` or cost-optimized `bulbul:v4-flash`), STT (`saaras:v4`), and chat (`sarvam-105b-conversations`), with automatic fallback to Groq (`openai/gpt-oss-20b`, `whisper-large-v3-turbo`) and browser Web Speech, backed by content-addressed `SHA-256` disk caching. |
| **Multi-Tenant Demo Security** | `app/demo_Lock.py`, `app/session_Isolation.py` | Per-visitor isolated SQLite sandboxes (`X-Demo-Session`), IP sliding-window rate limits, `DEMO_PIN` protection on paid provider calls, and `6` deterministic policy guardrails (`max 30%` discount, `Rs 500` single-wave cap, `14-day` cooldown, DPDP consent, supplier price cap, holdout preservation). |
| **Tamper-Evident Audit, Offline QR & Healthz** | `app/audit_qr.py`, `app/static/manifest.json` | Sequential `SHA-256` hash-chained audit export & tamper verifier (`/api/audit/export`), pure-Python ISO/IEC 18004 (`29x29`) offline SVG pass QR generator, `/api/healthz` `BEGIN IMMEDIATE` write-lock probe, and installable mobile companion PWA manifest. |
| **60-Case Multilingual Eval & CI Gate** | `scripts/eval_benchmark.py`, `.github/workflows/ci.yml`, `.dockerignore` | Automated `60/60` (`100%`) evaluation benchmark across EN/HI/KN/Indic-digit voice intents, `6` adversarial guardrail rules, and numeric grounding + Zero-PII checks, enforced in GitHub Actions CI alongside container layer secret hardening. |
| **Printable Closing Audit Report** | `app/pass_wallet.py` (`render_printable_closing_report_html`) | Self-contained, zero-network-dependency A4 HTML/print report summarizing KPIs, holdout scorecards, Grade A/B/C provenance, and recent audit events. |

---

## 3. Verified Reference Numbers (Default Synthetic Benchmark `seed = 20261025`)

All figures below come directly from the deterministic synthetic ledger (`Sri Krishna Darshini & Provisions`, Indiranagar) and are labelled honestly as synthetic/simulated:

* **60-Day QR Ledger (`Grade A` in app):** `1,613` UPI QR scans (`Rs 3,06,365` GMV); **30-day window:** `917` scans (`Rs 1,74,685` GMV, `Rs 190` average bill, `~30.6` scans/day); `240` unique customers (`175` repeat buyers with `3+` scans = `72.9%`).
* **Win-Back Funnel (`CMP-WINBACK-01`):** `48` silent evening regulars (absent `16 to 38` days) -> minus `5` without DPDP marketing consent -> minus `3` contacted in the last `14` days = **`40` eligible** -> **`32` With Offer** (`Rs 25` off `Rs 150+`, hard cap `Rs 300` = max `12` funded redemptions vs `Rs 800` uncapped exposure) + **`8` Holdout** (no message, no offer).
* **Simulated 48h Outcome (`Grade B` + `Grade C` assumptions):** `12/32` (`37.5%`) treatment return vs `1/8` (`12.5%`) holdout return -> estimated `4` organic + `8` incremental visits (`Rs 217.50` avg bill, `Rs 1,740` incremental sales, `Rs 522` gross profit at assumed `30%` margin, **`+Rs 222.00` pre-fee**, **`+Rs 91.50` post-5%-fee**; single-wave Fisher exact `p = 0.2364`, directional only).
* **Early-Warning Churn Care (`OPS-CARE-02`):** Flags `2` high-frequency morning regulars (`Sneha` and `Divya`, normal `2-day` gap, unseen `8` days) representing `Rs 4,920/month` historical spend at risk.
* **Modelled Monthly Unit Economics (`results/unit_economics.md`, `Grade C` assumptions):**
  * **Estimated Monthly COGS:** **`Rs 48.00 / merchant / month` cached** (`Rs 71.80` uncached = `Rs 1.80` SLM + `Rs 3.20` cached TTS / `Rs 27.00` uncached TTS + `Rs 43.00` WhatsApp/push notification delivery). Switching dynamic TTS to `bulbul:v4-flash` (`Rs 1.00 / 1K chars` vs `Rs 3.00 / 1K chars` on `v3`) lowers uncached voice synthesis cost by ~`67%`.
  * **Modelled Revenue Scenarios:** Case C (`Rs 79/mo` SaaS only -> `39.2%` cached gross margin); Case B (`Rs 79/mo` SaaS + assumed `5%` promo fee `Rs 102/mo` = `Rs 181/mo` -> **`73.5%` cached gross margin**); Case A (`Rs 258/mo` incl. assumed `Rs 77/mo` credit referral -> `81.4%` cached gross margin).

---

## 4. Verification & Reproducibility

Run the full 13-gate preflight audit, 60-case evaluation benchmark, and automated pytest suite locally:

```bash
python3 scripts/preflight.py
python3 scripts/eval_benchmark.py --assert-targets
pytest -v
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Key Portfolio Endpoints (`v1.8`)
* `GET /api/overview` - Full shop dashboard, RFM cohorts, campaigns, and store preset metadata.
* `GET /api/healthz` - Deep readiness probe (`SQLite` journal mode, `BEGIN IMMEDIATE` write-lock latency, `SHA-256` audit chain integrity, circuit-breaker status).
* `GET /api/audit/export` - Sequential `SHA-256` hash-chained audit export (`format=json` or `format=csv`).
* `POST /api/store/preset` - Live margin & break-even switching (`darshini`, `kirana`, `bakery`).
* `POST /api/ledger/upload-csv` - Zero-PII `SHA-256` UPI CSV ingestion & automatic campaign regeneration.
* `GET /api/campaigns/{id}/passes`, `GET /api/campaigns/{id}/pass-qr.svg`, & `POST /api/campaigns/{id}/scan-pass` - Pass wallet, pure-Python offline ISO-18004 SVG QR code, and atomic counter bill scanner (`min_bill` + `BEGIN IMMEDIATE` rupee cap).
* `POST /api/campaigns/{id}/whatsapp-preview` - Localized (`KN`/`HI`/`EN`) DPDP-compliant WhatsApp pass preview & optional PIN-locked Twilio Sandbox dispatch.
* `POST /api/pilot-simulate` - `1` to `200` shop pooled holdout statistical power & fleet ROI simulator.
* `GET /api/report/closing-summary` - Printable A4 Closing Profit & Holdout Audit Report.

---

## 5. Concise Resume Highlights (Ready to Use)

* **PaytmAI VyaparVoice (Full-Stack Fintech & Multilingual Voice AI Copilot):** Architected a voice-first merchant retention & causal attribution system in Python/FastAPI and SQLite (`WAL` + `BEGIN IMMEDIATE` atomic locking) separating deterministic rupee budget caps, DPDP consent checks, and `80/20` holdout lift math from Kannada/Hindi/English LLM & speech pipelines (`Sarvam saaras:v4`, `bulbul:v3`/`v4-flash`, `sarvam-105b-conversations`, `Groq` fallback).
* **Zero-PII Ledger Ingestion & Counter QR Pass Wallet:** Built in-memory `SHA-256` UPI CSV ingestion, dynamic store-category margin presets (`18%` kirana to `35%` bakery), atomic counter pass scanning with `50%/80%/100%` budget alerts, and a `1-to-200` shop pooled holdout power simulator (`Wilson 95% CI`, `Fisher exact`, `>80%` statistical power sizing).
