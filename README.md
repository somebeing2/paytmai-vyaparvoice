# PaytmAI VyaparVoice - Merchant Growth, Operations & Retention Assistant

**Live Render Demo:** [https://paytmai-vyaparvoice.onrender.com](https://paytmai-vyaparvoice.onrender.com)
**Track 1:** Merchant Growth AI | **Team:** SemiTechnical | **Author:** Kevin Joseph

**PaytmAI VyaparVoice** is a voice-first vernacular decision and retention prototype for neighbourhood kiranas and darshinis using Paytm QR and Soundbox (*Sri Krishna Darshini & Provisions, Indiranagar, Bengaluru*). It analyses a shop's QR payment ledger to spot silent regulars, dead-hour troughs, weekend stock spikes, and delayed frequent visitors, then reads a 3-sentence closing briefing in **Kannada, Hindi, or English**, accepts verbal or one-tap offer budgets (`Rs 50` to `Rs 2,500`) with mandatory readback confirmation, enforces hard spend caps with spoken `50%`, `80%`, and `100%` alerts, and measures returning visits against a randomized `80/20` non-offer holdout group without ever letting an LLM invent or alter a single number.

---

## Run Locally (Zero API Keys Required)

Every feature works out of the box with **zero API keys** using browser Web Speech and deterministic SQLite templates.

### Linux / macOS
```bash
git clone <repo-url>
cd paytmai-vyaparvoice
pip install -r requirements.txt
python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### Windows (PowerShell)
```powershell
git clone <repo-url>
Set-Location paytmai-vyaparvoice
$env:PYTHONUTF8 = "1"
pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open **`http://127.0.0.1:8000`** in Chrome or Edge.

---

## Testing & Verification Suite

Run the 12-gate automated preflight and QA suite (secret scan, `render.yaml` check, formatting hygiene, unit economics, Sarvam/Groq mocks, 4-mode failover matrix, `DEMO_PIN` & IP rate limits, cache seeding, and 21/21 baseline QA checks):

```bash
python3 scripts/preflight.py
```

---

## Architecture Overview

VyaparVoice is a **FastAPI + SQLite** single-service web application (`app/main.py`, `app/engine.py`, `app/stats.py`) serving a zero-build vanilla HTML/JS bilingual/trilingual interface (`app/static/index.html`, `app/static/i18n.js`). Each browser visitor receives an isolated, TTL-bounded SQLite session database (`app/sessions.py`) cloned from the seeded 60-day store ledger (`app/database.py`), while all financial waterfalls, Fisher exact tests, Wilson confidence intervals, Bayesian posteriors, and policy guardrails execute deterministically in Python. Speech and open-ended Q&A pass through a unified `ProviderRouter` (`app/providers/router.py`) backed by a persistent SQLite cache (`app/providers/persistent_cache.py`) and a strict numeric grounding gate (`verify_numeric_grounding`, normalizing ASCII, Devanagari, and Kannada digits) that rejects any model output containing an unverified number.

---

## Provider Fallback Order

All TTS, STT, and chat/plain-explanation requests follow a three-tier priority order across **English (`en-IN`), Hindi (`hi-IN`), and Kannada (`kn-IN`)**:

1. **Sarvam AI (Primary):** Active when `SARVAM_API_KEY` is set, call count is within `SARVAM_MAX_CALLS` and `SARVAM_SESSION_MAX_CALLS`, and live calls are permitted (`PUBLIC_DEPLOY=false`, or unlocked via `DEMO_PIN` / `DEMO_LIVE_UNLOCKED=true`). Uses `api-subscription-key` against `bulbul:v3` (`/text-to-speech`), `saaras:v4` (`/speech-to-text`, `10`-second max clip), and `sarvam-105b-conversations` (`/v1/chat/completions`).
2. **Groq (Secondary Fallback):** Active when Sarvam is unset, capped, or returns an HTTP/timeout error and `GROQ_API_KEY` is set. Uses `openai/gpt-oss-20b` (`/chat/completions`), `whisper-large-v3-turbo` (`/audio/transcriptions`), and `canopylabs/orpheus-v1-english` (`/audio/speech` for English).
3. **Browser Web Speech + Static Deterministic Templates (Tertiary Fallback):** Always available offline/keyless with zero external network calls.

Any Sarvam error, timeout, or quota cap falls back automatically and silently, surfacing only a small non-blocking notice in `Technical & Audit View`.

---

## Environment Variables

Copy `.env.example` to `.env` for local keys. `.env` is gitignored and is never logged, committed, or returned to the browser.

| Variable | Default When Empty | Purpose |
| :--- | :--- | :--- |
| `SARVAM_API_KEY` | *(empty)* | Primary Sarvam AI subscription key (`bulbul:v3` TTS, `saaras:v4` STT, `sarvam-105b-conversations` Chat). |
| `GROQ_API_KEY` | *(empty)* | Secondary Groq API key (`openai/gpt-oss-20b` Chat, `whisper-large-v3-turbo` STT, `canopylabs/orpheus-v1-english` TTS). |
| `SARVAM_MAX_CALLS` | `60` | Global hard ceiling on live Sarvam API calls before automatic fallback. |
| `SARVAM_SESSION_MAX_CALLS` | `35` | Per-visitor-session ceiling on live Sarvam API calls. |
| `PUBLIC_DEPLOY` | `false` locally / `true` on Render | Blocks unauthenticated public traffic from triggering live paid/credit API calls unless unlocked via `DEMO_PIN`. |
| `DEMO_PIN` | *(empty)* | Secret PIN set only in env vars; entering it in `Technical & Audit View` unlocks live Sarvam/Groq calls for that browser session only. |
| `DEMO_LIVE_UNLOCKED` | `false` | Optional server-side override flag to permit live calls on a private deployment without entering `DEMO_PIN`. |
| `RATE_LIMIT_PER_MINUTE` | `30` | Per-IP sliding-window limit per minute on all endpoints that can trigger model or audio calls. |
| `STT_TTS_PROVIDER` | `auto` | `auto` (`Sarvam` -> `Groq` -> `Web Speech`), `sarvam`, `groq`, or `webspeech`. |
| `LLM_PROVIDER` | `auto` | `auto` (`Sarvam` -> `Groq` -> `template`), `sarvam`, `groq`, or `template`. |

---

## Pre-Warm & Cache Seeding for Render's Ephemeral Disk

Render Free instances use an ephemeral filesystem that resets on redeploy or sleep. To ship real Sarvam audio for all `30` fixed EN/HI/KN phrases (`27` unique clips) so public visitors hear authentic Sarvam voices at **zero runtime API calls**:

1. Set `SARVAM_API_KEY` in your local `.env` (with `PUBLIC_DEPLOY=false`) and start the app locally.
2. Open **Technical & Audit View** and click **Pre-warm Fixed Phrases (EN/HI/KN)** (or run `curl -X POST http://127.0.0.1:8000/api/providers/prewarm`).
3. Export the cached fixed-phrase WAV files and clean manifest (`provider`, `language`, `voice`, `exact_text` only; zero keys, PINs, user data, or logs) into `assets/prewarmed/`:
   ```bash
   python3 scripts/export_prewarmed.py
   ```
4. Commit and push `assets/prewarmed/`:
   ```bash
   git add assets/prewarmed
   git commit -m "chore(cache): seed pre-warmed EN/HI/KN fixed-phrase audio"
   git push origin main
   ```
5. On startup, VyaparVoice automatically seeds `data/provider_cache.db` from `assets/prewarmed/` with zero API calls (if `assets/prewarmed/` is empty or missing, startup proceeds normally using fallbacks).

---

## DEMO_PIN Gating (Protecting API Credits on Public Links)

Because the live Render URL is public, `PUBLIC_DEPLOY=true` is enabled automatically on Render to prevent bots or anonymous traffic from draining Sarvam or Groq trial credits:

- **Default Locked Visitor Mode:** Public visitors still get full interactive SQLite sessions, deterministic EN/HI/KN voice answers, and zero-cost playback of any pre-warmed audio in `assets/prewarmed/`, with fallback to browser Web Speech for uncached phrases.
- **Unlocking Live Calls During a Judge Demo:** Switch to **Technical & Audit View**, enter the `DEMO_PIN` (configured only in Render Environment Variables), and click **Unlock Live Demo**. Only your browser session is unlocked for live `saaras:v4` STT, `bulbul:v3` TTS, and `sarvam-105b-conversations` Q&A; click **Lock Demo** when finished.

---

## Render Deployment & `/health` Wake Check

`render.yaml` is included at repository root:
- **Build command:** `pip install -r requirements.txt`
- **Start command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **Environment variable names to configure in Render Dashboard -> Environment (values set privately in Render, never in git):**
  `SARVAM_API_KEY`, `GROQ_API_KEY`, `SARVAM_MAX_CALLS`, `SARVAM_SESSION_MAX_CALLS`, `PUBLIC_DEPLOY`, `DEMO_PIN`, `RATE_LIMIT_PER_MINUTE`, `DEMO_LIVE_UNLOCKED`.

**Render Free-Tier 15-Minute Sleep & Health Check:** Render Free web services spin down after **15 minutes** of inactivity (`30` to `50` seconds cold start). Ping `/health` 2 minutes before a live demo to wake the container and verify readiness:

```bash
curl -i https://paytmai-vyaparvoice.onrender.com/health
```

---

## Limitations

1. **Synthetic 60-Day Sample Ledger:** All store metrics (`240` customers, `1,613` historical QR transactions ending on `25 October 2026`, `seed = 20261025`) come from a deterministic synthetic ledger modelling a Bengaluru darshini and provisions store, not live production Paytm merchant data.
2. **Unreviewed Vernacular Drafts:** All Hindi and Kannada strings and voice scripts are marked `"Draft - unreviewed by native speaker"` and require native-speaker copy review before production merchant rollout.
3. **Proposed Voice-Device Interaction Design:** Two-way spoken budget setting and Q&A on an AI Soundbox or Paytm for Business companion interface is a proposed product workflow; this prototype captures spoken input (capped at `10` seconds) via the browser microphone with editable transcript and typed/chip fallbacks.
4. **Modelled Profit & Single-Shop Sample Size:** Profit figures (`Grade C`) rely on explicit assumptions (`30%` gross shop margin and `5%` Paytm promo fee on redeemed bills) not observable on raw UPI receipts, and a single-shop `40`-customer wave (`32` with offer vs `8` holdout) is directional (`p = 0.2364`); validating true incremental lift requires a live pooled multi-shop randomized control trial (`n >= 2,000` across ~`50` shops).
