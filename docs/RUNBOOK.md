# PaytmAI VyaparVoice - One-Page Finals Day Runbook (Saturday 31 Oct 2026)

- **Team:** SemiTechnical (`Kevin Joseph`) | **Track:** Track 1 - Merchant Growth AI
- **Primary Demo Mode:** Localhost `http://127.0.0.1:8000` (zero cloud cold-start latency, zero Wi-Fi dependency)
- **Public Cloud URL:** `https://paytmai-vyaparvoice.onrender.com` (per-visitor isolated SQLite sessions; paid API calls locked off)

---

## 1. T-Minus 15 Minutes Before Any Judging Round

1. **Start Local Server (Primary):**
   ```bash
   make preflight
   python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```
2. **Open & Verify Tabs:**
   - Tab 1: `http://127.0.0.1:8000` (click **Reset Session**, verify `Rs 1,74,685` 30d sales, test audio volume at 70%).
   - Tab 2: `deck/v2/PaytmAI_VyaparVoice_v2.pdf` (or `deck/v1/PaytmAI_VyaparVoice_v1.pdf` prior to Deck v2 build), full-screen ready on Slide 1.
3. **Warm Up Public Render URL (If Judges Want to Scan Slide 2 QR):**
   - Render free plan spins down after 15 minutes idle (~60s cold start). Hit `https://paytmai-vyaparvoice.onrender.com/api/health` from your phone hotspot **2 minutes before** walking up to the table or stage.
4. **Network Backup:** Keep phone USB/Wi-Fi hotspot armed, though `127.0.0.1:8000` + cached audio / browser Web Speech works offline.

---

## 2. Saturday 11:00 AM to 1:00 PM Sponsor Build Window (Sarvam AI 500 Credits)

> **Security Rule:** Put `SARVAM_API_KEY` ONLY inside your local untracked `.env` file on your laptop. Never paste it into tracked files, chat, or Render public env vars without `PUBLIC_DEPLOY=true` protection.

1. Edit local `.env` (untracked):
   ```ini
   PUBLIC_DEPLOY=false
   SARVAM_ENABLED=true
   SARVAM_LIVE_CALLS_ENABLED=true
   SARVAM_API_KEY=<paste_your_sponsor_key_locally_only>
   ```
2. Initialize the universal credit ledger (`15%` TTS cap = `75` credits, `15%` STT cap = `75` credits, `30%` combined hard ceiling = `150` credits):
   ```bash
   make ledger-set-balance CREDITS=500
   ```
3. Run live self-test and pre-generate cached `.wav` audio for `en`, `kn`, and `hi` 8:30 PM briefings:
   ```bash
   python3 scripts/sarvam_cli.py selftest --live
   make activate-sarvam
   ```
4. Once `make activate-sarvam` succeeds, `data/audio_cache/` holds all three briefings locally (`0` credits per replay on stage!). You may even set `SARVAM_LIVE_CALLS_ENABLED=false` afterward so stage playback uses `Sarvam Cached Audio` deterministically with zero network risk.
5. **Only if step 3 & 4 pass**, switch from the Default voice line in `docs/SCRIPTS.md` to the **Saturday Swap-In Line**. If Sarvam returns any `401/402/429/5xx` error, the circuit breaker halts automatically and the app falls back to Browser Web Speech.

---

## 3. On-Stage Failure Recovery Order

1. **Mic noisy on stage:** Click the built-in simulated voice chip (`"Haudu / Haan, Approve"`) directly below the Soundbox LCD.
2. **Audio muted on HDMI:** Point to the live text transcript box + toggle **Merchant View** / **Technical & Audit View** visually.
3. **Browser or port conflict:** Switch immediately to the open PDF deck (`Slide 3` + `Appendix A4` + `Slide 4`) using the **Emergency Deck-Only Fallback Bridge** in `docs/SCRIPTS.md`.
