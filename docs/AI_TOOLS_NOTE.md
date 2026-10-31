# AI Tools, Runtime Models & Safeguards Note

- **Project:** PaytmAI VyaparVoice (`v1.5.0` / `v1.0-finals`)
- **Team:** SemiTechnical (`Kevin Joseph`)
- **Scope:** Factual summary of AI tools used during development and AI models invoked at runtime, grounded in the repository, git history, and `AGENT_HANDOFF.md`.

---

## 1. AI Tools Used During Development

- **Chat Planning & Review Assistant:** An AI assistant (Claude, by Anthropic) was used in chat for planning, drafting prompts for the coding agent, and reviewing the agent's outputs.
- **AI Coding Agent:** Repository commits and `AGENT_HANDOFF.md` record the use of an AI coding agent in an iterative pair-programming workflow across architecture scaffolding, FastAPI routes (`app/main.py`), SQLite ledger and atomic cap logic (`app/database.py`, `app/engine.py`), Sarvam and Groq provider adapters (`app/providers/`), multilingual UI strings (`app/static/i18n.js`, `app/templates.py`), automated regression suites (`tests/*.py`, `scripts/preflight.py`), and submission documentation. Specific coding agent name and underlying model (not recorded in repository commits, commit trailers, or handoff files): **to be confirmed by the team**.
- **Translation Drafting:** Draft Hindi (`hi`) and Kannada (`kn`) UI strings and spoken templates were generated with AI assistance and parameterised in code; every Hindi and Kannada screen carries the explicit status badge `"Draft - unreviewed by native speaker"`. Native speaker review status outside the repository is **to be confirmed by the team**.

---

## 2. Runtime AI Models & Fallback Roles in the Application

VyaparVoice uses a three-tier runtime router (`app/providers/router.py`) controlled by `STT_TTS_PROVIDER` and `LLM_PROVIDER`:

### Tier 1: Sarvam AI (Primary Provider for EN, HI, KN)
- **`bulbul:v3` (Text-to-Speech, `POST /text-to-speech`):** Generates `22050 Hz` WAV audio for Soundbox briefings, `50%`/`80%`/`100%` budget alerts, `Explain Simply` readouts, and voice answers (`priya` for `en-IN`/`kn-IN`, `shubh` for `hi-IN`).
- **`saaras:v4` (Speech-to-Text, `POST /speech-to-text`):** Transcribes browser microphone recordings (hard-capped at `10` seconds) in Kannada (`kn-IN`), Hindi (`hi-IN`), and Indian English (`en-IN`).
- **`sarvam-105b-conversations` (Chat Completions, `POST /v1/chat/completions`):** Handles open-ended merchant questions (`temperature=0.1`, `max_tokens=110`) and optional plain-language `Explain Simply` phrasing over sanitized store facts (`sarvam-105b` is documented in `config/sarvam.yaml` for offline reasoning reference only).

### Tier 2: Groq (Secondary Failover Provider)
- **`openai/gpt-oss-20b` (`POST /openai/v1/chat/completions`):** Secondary grounded Q&A and plain-language phrasing model (`temperature=0.1`, `max_tokens=140`) if Sarvam is unconfigured, rate-limited, or over its call cap.
- **`whisper-large-v3-turbo` (`POST /openai/v1/audio/transcriptions`):** Secondary multilingual STT failover (`en`, `hi`, `kn`).
- **`canopylabs/orpheus-v1-english` (`POST /openai/v1/audio/speech`):** Secondary English TTS failover (voice `troy`); Hindi and Kannada TTS fall back directly to Browser Web Speech if Sarvam TTS is unavailable.

### Tier 3: Browser Web Speech API + Deterministic Templates (Zero-Cost Fallback)
- **`window.speechSynthesis` and `window.SpeechRecognition`:** Client-side browser speech paired with deterministic SQLite answer templates (`build_deterministic_store_answer` and `render_static_plain_explanation`) in English, Hindi, and Kannada, guaranteeing uninterrupted operation with zero external API keys.

---

## 3. Deterministic Safeguards Against Hallucination, PII Leakage & Credit Drain

1. **Zero LLM Arithmetic:** Every rupee figure, scan count, holdout percentage, Wilson confidence interval, Fisher exact `p`-value, and profit waterfall line is computed deterministically in Python (`app/engine.py`, `app/explain_simply.py`) from SQLite (`data/vyaparvoice.db`).
2. **Deterministic Intent Routing First:** High-frequency questions (`customers today`, `profit`, `repeat` / `total customers`, `spend and remaining`, `why 40`, `max loss`, `after cap`, `milk`, and `help`) are answered directly from SQLite templates with zero LLM calls.
3. **Zero-PII Outbound Payloads:** `build_sanitized_store_facts` strips customer names, customer IDs, phone numbers, and UPI handles before any external request, enforced at runtime by `assert_zero_pii`.
4. **Multilingual Numeric Grounding Gate:** `verify_numeric_grounding` (Q&A) and `validate_llm_plain_output` (`Explain Simply`) normalize ASCII (`0-9`), Devanagari (`०-९`), and Kannada (`೦-೯`) digits and reject any LLM output containing a number absent from the code-supplied facts, reverting automatically to deterministic SQLite templates.
5. **Policy, Jargon & Prompt-Injection Guardrails:** `evaluate_guardrail_attack` blocks prompt-injection strings and enforces DPDP consent, `14`-day cooldown, `<= 22%` discount limits, `Rs 50` to `Rs 2,500` budget bounds, and `80/20` holdouts; `find_plain_jargon_violations` blocks statistical jargon in `Explain Simply`.
6. **Persistent Caching & Access Control:** `PersistentProviderCache` (`data/provider_cache.db`, seeded on startup from `assets/prewarmed/` when populated), `SARVAM_MAX_CALLS=60` global / `35` per-session limits, `30%` credit ceiling, `30/min` per-IP rate limiting, and constant-time `DEMO_PIN` gating on public Render (`PUBLIC_DEPLOY=true`) prevent accidental credit exhaustion.

---

## 4. Division of Decisions: Human vs Coding Agent

- **Evidenced in Repository Prompts, Commits & Configuration (`Kevin Joseph`):** Selection of Track 1 (Merchant Growth AI) and the customer-loss problem framing; requirement for hard rupee stop-loss caps, `80/20` holdout measurement, and three-tier (`A`/`B`/`C`) evidence grading; selection of Sarvam AI (primary EN/HI/KN) and Groq (secondary) plus Render deployment target; public `DEMO_PIN` security rules and API credit conservation limits; honest disclosures covering synthetic data, assumed `30%` margin and `5%` promo fee, inferred post-rush causes (`"possibly after a busy rush"`), `"Monthly spend at risk"`, and hardware scope (to our knowledge the standard Paytm Soundbox is speaker-based with no microphone; this is to be validated with Paytm). Any additional off-repo product research, merchant interviews, or manual IDE edits are **to be confirmed by the team**.
- **Implemented by the AI Coding Agent (Under Human Specification & Verification):** FastAPI/SQLite implementation, deterministic synthetic ledger generator (`seed = 20261025`), atomic `BEGIN IMMEDIATE` redemption engine, statistical/Bayesian evaluation functions, Sarvam and Groq HTTP clients, multilingual UI (`en`/`hi`/`kn`), `Explain Simply` module, persistent cache and pre-warm export scripts, and automated preflight test suites.

---

## 5. Human Verification

- **Automated Preflight Suite (`scripts/preflight.py`):** `12/12` automated verification gates enforced in the repository (`render.yaml` diff check, formatting hygiene lint across source/test/doc files, reproducible unit economics check, keyless Sarvam mock selftest, and full test execution).
- **Automated Test Suites (`tests/*.py` & `scripts/qa_battery.py`):** `7` automated suites containing `311` Python `assert` checks plus the `21/21` end-to-end QA battery across Sarvam, Groq, and fallback modes.
- **Repository & History Secret Scan:** Automated scan in `scripts/preflight.py` verifying zero `.env` files or API/token secret patterns across tracked files and git history.
- Manual testing by the team: to be confirmed by the team
