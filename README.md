# PaytmAI VyaparVoice - Merchant Growth, Operations & Retention Autopilot

[![Live Demo](https://img.shields.io/badge/LIVE_DEMO-Open_Soundbox_App-00BAF2?style=for-the-badge&logo=render&logoColor=white)](https://paytmai-vyaparvoice.onrender.com)
![Track](https://img.shields.io/badge/Track_1-Merchant_Growth_AI-00BAF2?style=for-the-badge)
![Stack](https://img.shields.io/badge/FastAPI_%2B_SQLite-Vernacular_Voice-002970?style=for-the-badge)
![QA Battery](https://img.shields.io/badge/Preflight_Suite-11%2F11_Gates_Passing-059669?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-slate?style=for-the-badge)

> **Paytm Build for India AI Hackathon - Bengaluru Finals Edition**
> **Track 1:** Merchant Growth AI (*Build the AI business partner for every Paytm merchant*)
> **Team Name:** SemiTechnical | **Member Name:** Kevin Joseph

---

## Live MVP Interface Preview

![PaytmAI VyaparVoice Live Dashboard](./docs/screenshots/dashboard-roi-proof.png)

---

## Overview

**PaytmAI VyaparVoice** turns Paytm's **AI Soundbox + Paytm for Business** into a voice-first vernacular growth, operations, and customer-care copilot for neighbourhood kiranas and darshinis (*Sri Krishna Darshini & Provisions, Indiranagar, Bengaluru*).

### Core Finals Capabilities
1. **Full Merchant View Localisation (`en`, `hi`, `kn`):** Single global language state persisted in `localStorage` (defaulting to the merchant profile language `kn`), translating every Merchant View string, button, status badge, parameterised offer card, KPI card, and audit entry with Indian number formatting (`en-IN`) and `Noto Sans` / `Noto Sans Devanagari` / `Noto Sans Kannada` web fonts. Hindi and Kannada content carry the explicit `"Draft - unreviewed by native speaker"` badge, while `Technical & Audit View` stays strictly in English.
2. **Voice-First 3-Sentence Soundbox Briefing:** Default Soundbox briefing delivers 2 to 3 crisp sentences (today's headline, offer status, and one suggested action) with `"Hear details"` for the full readout, `"Speak"` playback via Sarvam `bulbul:v3` or browser Web Speech, and graceful missing-voice handling for Kannada/Hindi.
3. **Verbal Budget Setting with Mandatory Readback Confirmation:** Accepts English, Hindi, and Kannada spoken or typed budget commands (`"set my offer budget to one thousand rupees for this week"`), parses digits and number words deterministically first, shows an editable transcript for noisy shop floors, enforces `Rs 50` to `Rs 2,500` bounds, reads back `"Offer budget of Rs {amount} for {period}. Say yes to confirm."`, and records `source="voice"` or `source="dashboard"` in the immutable audit log.
4. **Spoken `50%`, `80%`, and `100%` Threshold Alerts:** Fires each threshold once per campaign (persisted in SQLite and logged in `audit_logs`), speaks and displays in the active language, offers voice/tap `"extend"` (via confirmed budget flow) or `"stop"` at `80%`, and includes a `"Simulate spend"` demo control in `Technical & Audit View`.
5. **Automatic `100%` Cap Pause & Regular-Price Continuity:** Automatically pauses cashback issuance at `100%` of cap so spend never exceeds `max_budget`; subsequent customers are billed at regular price (zero turned away), with spoken and visual return-per-rupee summary suggesting extension only when net return per rupee is positive.
6. **Jargon-Free `"Explain simply"` Results:** Plain everyday explanations in `en`, `hi`, and `kn` for cap performance, offer vs non-offer buyers, and spend vs return (`"uplift"`, `"control group"`, `"break-even"` banned), backed by strict code-supplied numbers and an LLM number-match validator that falls back to deterministic templates if any number differs.
7. **Deterministic Guardrails & Financial Honesty:** Every number, amount, count, date, and percentage is computed in Python/SQLite (`240` customers, `1,613` historical UPI transactions). Evidence grades (`Grade A` observed ledger, `Grade B` simulated holdout, `Grade C` margin/fee assumptions) and pre-run / break-even states are labelled explicitly.

---

## Quickstart (Zero API Keys Required)

Every feature works out of the box with **zero API keys set** using browser Web Speech + deterministic SQLite templates.

### Option A: Windows (PowerShell)
```powershell
Set-Location "$HOME\paytmai-vyaparvoice"
$env:PYTHONUTF8 = "1"
pip install -r requirements.txt
python scripts\preflight.py
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```
Open **`http://127.0.0.1:8000`** in Chrome or Edge.

### Option B: Linux / macOS
```bash
cd paytmai-vyaparvoice
pip install -r requirements.txt
python3 scripts/preflight.py
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## Environment Variables & Provider Switches

`.env` is listed in `.gitignore` and must never be committed. Copy `.env.example` to `.env` for local configuration:

| Variable | Default | Purpose |
| :--- | :--- | :--- |
| `SARVAM_API_KEY` | *(empty)* | Sarvam AI subscription key (`bulbul:v3` TTS + `saaras:v3` STT). When empty, falls back cleanly to browser Web Speech. |
| `GROQ_API_KEY` | *(empty)* | Groq free-tier API key for grounded merchant Q&A and number-verified plain phrasing. When empty, falls back to deterministic SQLite templates. |
| `STT_TTS_PROVIDER` | `auto` | `auto` (uses Sarvam when `SARVAM_API_KEY` is set, else `webspeech`), `sarvam`, or `webspeech` (forces browser Web Speech even if a key exists). |
| `LLM_PROVIDER` | `auto` | `auto` (uses Groq when `GROQ_API_KEY` is set, else `template`), `groq`, or `template` (forces static deterministic templates). |
| `GROQ_MODEL` | `openai/gpt-oss-20b` | Free-tier Groq chat completion model identifier (`llama-3.1-8b-instant` or `openai/gpt-oss-20b`). |
| `PUBLIC_DEPLOY` | `false` locally / `true` on Render | When `true`, hard-blocks outbound paid/credit API calls (`assert_paid_calls_permitted`) so public traffic cannot drain keys; cached WAV audio in `data/audio_cache/` still plays at zero credit cost. |
| `ISOLATE_VISITORS` | `true` | Isolates each browser visitor into a bounded per-session SQLite copy (`app/sessions_db/`). |
| `ADMIN_TOKEN` | *(empty)* | Token protecting `/api/admin/reset-global` and `/api/admin/provider-status`. |
| `PORT` | `8000` | HTTP port bound by Uvicorn (`0.0.0.0:$PORT` on Render). |

---

## How to Enable Sarvam AI with One Key

No code changes are required to switch from browser Web Speech to live Sarvam AI (`bulbul:v3` TTS + `saaras:v3` STT):

1. Create a local `.env` file (ignored by git) with a single line:
   ```ini
   SARVAM_API_KEY=<paste-in-local-dotenv>
   ```
2. Because `STT_TTS_PROVIDER` defaults to `auto` (and `PUBLIC_DEPLOY` defaults to `false` locally), restarting `uvicorn app.main:app` immediately enables live Sarvam TTS (`priya` for `en-IN` and `kn-IN`, `shubh` for `hi-IN`) and Sarvam `saaras:v3` STT, caching generated WAV clips under `data/audio_cache/`.
3. Optional CLI pre-cache & credit budget check (`<= 15%` TTS cap, `~4` credits total for all 3 languages):
   ```bash
   python3 scripts/sarvam_cli.py status
   python3 scripts/sarvam_cli.py activate --credits 100
   ```
4. To force fallback mode at any time without deleting your key, set `STT_TTS_PROVIDER=webspeech` or `LLM_PROVIDER=template` in `.env`.

---

## Deploying on Render & 15-Minute Free-Tier Sleep Notice

1. Push the repository to GitHub (`render.yaml` and `Dockerfile` are pre-configured at repository root).
2. In the Render Dashboard, select **New -> Blueprint** (or **New -> Web Service**) and connect the repository:
   - Render builds from `Dockerfile` and binds `0.0.0.0:$PORT` immediately while seeding SQLite in a background thread.
   - `PUBLIC_DEPLOY=true` is enabled automatically on Render (`RENDER=true`) to protect API credits from public traffic while serving pre-cached WAV audio and full isolated visitor sessions.
   - If you choose to configure environment variables on a private Render instance, add them in **Render Dashboard -> Environment** (never in tracked files).
3. **Important - Render Free Instance 15-Minute Inactivity Sleep:**
   - **Render Free web services automatically spin down after 15 minutes of inactivity**, and the first cold-start request can take 30 to 50 seconds to wake the container.
   - **Always ping `GET /health` 2 to 3 minutes before starting a live demo** to wake the instance and verify readiness:
     ```bash
     curl -i https://paytmai-vyaparvoice.onrender.com/health
     ```
     Or in Windows PowerShell:
     ```powershell
     Invoke-RestMethod "https://paytmai-vyaparvoice.onrender.com/health" | Format-List
     ```

---

## Key REST Endpoints (`/docs` for OpenAPI UI)

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/health` (and `/api/health`) | Fast health & readiness check (use to wake Render free tier before demo) |
| `GET` | `/api/overview` | Live 30d KPIs, profit state, campaigns, threshold alerts, cap summary & audit logs |
| `GET` | `/api/briefing?lang=en\|kn\|hi&detail=false` | 3-sentence voice-first Soundbox briefing (`detail=true` for full version) |
| `POST` | `/api/tts` & `POST /api/stt` | Active TTS / STT provider bridge (Sarvam when enabled, Web Speech fallback otherwise) |
| `POST` | `/api/voice-command` | Multilingual verbal budget parser, yes/no confirmation, extend/stop & ops commands |
| `POST` | `/api/campaigns/{id}/cap` | Cap editor (`Rs 50` to `Rs 2,500`) with two-step confirmation & `source` audit logging |
| `POST` | `/api/campaigns/{id}/simulate-spend` | Technical View live spend simulator (`50%`, `80%`, `100%`, post-cap regular bills) |
| `GET` | `/api/campaigns/{id}/explain-simply?lang=...` | Jargon-free plain explanation in `en`, `hi`, `kn` with strict number verification |
| `GET` | `/api/why/{id}` | Plain + technical provenance drawer (`CMP-WINBACK-01`, `KPI-PROFIT`, etc.) |
| `POST` | `/api/reset` | Reset isolated visitor session back to fresh 8:30 PM closing state |

---

Built for India's small businesses by **Kevin Joseph (Team SemiTechnical)**.
