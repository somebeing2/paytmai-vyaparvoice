# PaytmAI VyaparVoice: Founder & Technical Project Explainer

- **Product:** PaytmAI VyaparVoice (Track 1: Merchant Growth AI, Paytm Build for India AI Hackathon)
- **Team:** SemiTechnical | **Founder / Engineer:** Kevin Joseph
- **Live Demo:** https://paytmai-vyaparvoice.onrender.com/
- **Repository:** https://github.com/somebeing2/paytmai-vyaparvoice

---

## 0. Eight Hardest Questions (15-Second Answers)

1. **Why use simulated data instead of real shop data?**
   Real merchant UPI ledgers contain private payer records we cannot publish in a hackathon repo. We use a deterministic 60-day synthetic ledger (`seed = 20261025`, `240` buyers, `1,613` scans) to prove the cap, holdout, grounding, and voice mechanics end to end, and label every result synthetic or simulated.
2. **Do the economics break for low-margin kiranas (`15%` to `20%` margin)?**
   Yes, for a `Rs 25` off `Rs 150` offer: under an assumed `5%` promo fee, break-even shop margin is `24.7%` (`-Rs 82.50` at `20%` margin vs `+Rs 91.50` at an assumed `30%` darshini margin). VyaparVoice suits darshinis first; low-margin kiranas need smaller category presets (`Rs 10` to `Rs 15` on `Rs 250+` bills).
3. **Does the Paytm Soundbox have a microphone?**
   To our knowledge the standard Paytm Soundbox is speaker-based with no microphone; this is to be validated with Paytm. In our architecture, Soundbox speaks briefings and alerts while spoken replies go through the Paytm for Business app (or a voice-enabled device), with the browser microphone standing in during the demo.
4. **Is one `40`-customer wave statistically significant?**
   No. In our simulation, `12/32` (`37.5%`) vs `1/8` (`12.5%`) gives two-sided Fisher exact `p = 0.2364` and Bayesian `P(post-fee profit > 0) = 52.1%`, so a single wave is directional only. Pooling `50` opt-in shops (`n = 2,000`: `1,600` offer, `400` holdout) reaches `92.5%` power at `+7` percentage points.
5. **How does this differ from existing Paytm Soundbox or merchant features?**
   To our knowledge, standard Soundbox audio announces individual payments as they arrive (`assumption, to verify with Paytm`). VyaparVoice analyses multi-week scan gaps across repeat payers, enforces an atomic rupee budget cap (`Rs 300`), holds out `20%` without an offer to subtract organic walk-ins, and logs every approval.
6. **How do you handle customer privacy and DPDP compliance?**
   Campaign eligibility requires `dpdp_consent = 1` (`5` of `48` silent regulars excluded) plus a `14`-day cooldown (`3` more excluded). Before any prompt reaches Sarvam or Groq, `build_sanitized_store_facts` and `assert_zero_pii` strip all customer names, IDs, phone numbers, and UPI handles.
7. **What is the monthly cost per merchant?**
   `Rs 48/month` cached (`Rs 71.80/month` uncached) is a **modelled assumption** from `scripts/unit_economics.py` (`Rs 3.20` cached TTS, `Rs 1.80` compute, `Rs 43.00` messaging). WhatsApp or push delivery costs (`Rs 43.00`) are modelled assumptions only, not messages the prototype app actually sends.
8. **How would this scale beyond the demo?**
   For isolated hackathon judging on Render Free (`512 MB` RAM), each visitor gets a `~233 KB` SQLite file (`64`-session LRU, `30`-minute TTL). Production scale would replace per-session SQLite files with partitioned merchant ledger tables and atomic server-side budget counters integrated into Paytm's backend (`assumption, to verify with Paytm`).

---

## 1. End-to-End Overview & Four Delivery Layers

Neighbourhood darshinis and kiranas lose repeat buyers quietly: regulars stop visiting after a slow rush-hour queue or drift away over two to five weeks, while owners fear uncapped discounts. **PaytmAI VyaparVoice** runs a four-step loop (**detect, propose, cap, measure**) on QR scan timestamps, using voice in **Kannada, Hindi, and English** as the delivery layer rather than framing dashboard literacy as the problem:

1. **Layer 1 - Spoken First on Soundbox `[BUILT in web audio; physical Soundbox playback PROPOSED]`:** Closing 3-sentence briefing (`111` today/recent QR payments, `32` silent regulars, `Rs 300` cap) plus spoken `50%`, `80%`, and `100%` cap alerts. Spoken replies use the browser mic in the demo as a stand-in for the **Paytm for Business app** `[PROPOSED]`, since to our knowledge the standard Paytm Soundbox is speaker-based with no microphone; this is to be validated with Paytm.
2. **Layer 2 - `Explain Simply` on Request `[BUILT]`:** Reads three jargon-free sentences (`cap`, `visitor comparison`, `spend vs return`) in `kn`, `hi`, or `en` using Python-computed integers and templates (or digit-verified LLM phrasing).
3. **Layer 3 - Translated Merchant View with `Why?` Panels `[BUILT web UI; Paytm app tab PROPOSED]`:** Optional `kn`/`hi`/`en` screen (`Draft - unreviewed by native speaker` on `hi`/`kn`) with a `Why?` drawer and Evidence Grade (`A`/`B`/`C`) on every card.
4. **Layer 4 - Technical & Audit View `[BUILT]`:** English risk/judge console exposing `audit_logs`, policy guardrails, `Provider in use`, `Sarvam calls`, SQLite cache count, `Pre-warm`, `DEMO_PIN` lock, and sensitivity tables.

---

## 2. Walkthrough of One Merchant Day & Core Features Under the Hood

1. **8:30 PM Closing Briefing (`app/engine.py:get_voice_briefing`):** Reads `111` QR payments, `32` eligible lapsed regulars (`Rs 25` off `Rs 150+` within a `Rs 300` cap, `8` held out), and a prompt to approve (`Hear details` expands to 6 sentences; `0` passive API calls on load).
2. **Verbal Budget + Readback (`parse_verbal_budget_command`):** Parses `en`/`hi`/`kn` spoken or typed caps (`Rs 50` to `Rs 2,500`) and time windows (`"for this week"`), reads back exact terms, and writes to `campaigns` + `audit_logs` only after explicit confirmation.
3. **Live Cap Alerts & Atomic Pause (`redeem_single_pass_atomic`):** Executes each pass redemption inside a `BEGIN IMMEDIATE` SQLite transaction, fires one-time spoken/visual alerts at `50%` (`Rs 150`), `80%` (`Rs 250`), and `100%` (`Rs 300`), and sets `CAP_PAUSED` so later customers pay regular price.
4. **Deterministic Voice Q&A (`detect_common_qa_intent`) & Guardrails (`evaluate_guardrail_attack`):** Answers common questions (`customers today`, `profit`, `repeat customers`, `spend & remaining`, `why 40`, `max loss`, `after cap`, `milk`) directly from SQLite with `0` LLM calls, and enforces DPDP opt-in, `14`-day cooldown, `<= 22%` discount limit, `80/20` holdout, and prompt-injection blocking.
5. **Post-Rush Delayed Regulars (`detect_delayed_regulars_from_ledger`):** Flags frequent regulars (`12+` visits, median gap `1.5` to `3.0` days) silent `8+` days whose last scan fell in a `>= 6`-scan peak slot, framing the cause strictly as inferred (`"possibly after a busy rush"`, zero payment star-rating tags; standard QR receipts do not include star ratings, `assumption, to verify with Paytm`).

---

## 3. How Simulated 48-Hour Return Outcomes Are Generated in Source Code

In `app/engine.py` (`_draw_independent_outcomes`, lines `1610-1652`, called by `simulate_campaign_48h`), the 48-hour outcomes are **illustrative simulations and NOT empirical evidence of customer lift**:

- **Default `mode="canonical"` (used by the UI `Complete 48h Run` button):** Returns fixed deterministic counts so every demo session reproduces identical arithmetic. For `CMP-WINBACK-01`, `canonical_t_ret = 12` selects the first `12` of `32` assigned treatment buyers (`37.5%`) with deterministic bills `210 + ((idx % 4) * 15) - 15` (`Rs 195, 210, 225, 240` x `3` = `Rs 2,610`, mean `Rs 217.50`), and sets `canonical_h_ret = 1` of `8` holdout buyers (`12.5%`). For `CMP-DEADHOUR-02`, `canonical_t_ret = 11` of `27` (`40.7%`, base `Rs 155`) vs `canonical_h_ret = 1` of `7` (`14.3%`).
- **Optional `mode="stochastic"` (used in Monte Carlo / sensitivity helpers):** Seeds `random.Random(f"{campaign_id}:{seed}:{offer_rupees}")` (`seed = 20261025`) with assumed baseline `p_base = 0.125` (`0.143` dead-hour) and assumed response curve `p_treat = p_base + (0.50 - p_base) * (1 - exp(-offer_rupees / 22.0))` (`38.0%` at `Rs 25`).

---

## 4. Exact Arithmetic of Headline Figures (Synthetic 60-Day Ledger, Seed `20261025`)

- **Store Baseline (`Grade A` synthetic):** `Rs 1,74,685` 30-day QR sales across `917` scans (`1,613` in 60 days); `Rs 190` avg bill; `240` unique buyers (`175` with `3+` scans = `72.9%` repeat). Latest sample day (`25 October 2026` in `ledger_meta`): `9` buyers, `9` scans, `Rs 1,750`.
- **Win-Back Funnel (`CMP-WINBACK-01`, `Grade A`):** `48` silent regulars (`16` to `38` days) minus `5` without consent (`43`) minus `3` in `14`-day cooldown = **`40` eligible** -> **`32` offer / `8` holdout** (`Rs 25` off `Rs 150+`, `Rs 300` cap = `12` funded bills vs `Rs 800` face exposure; `42.2%` binomial overrun risk -> suggests `Rs 400`).
- **Delayed Regulars `Monthly spend at risk` (`OPS-CARE-02`, `Grade A` historical arithmetic):** `2` regulars (`Sneha` + `Divya`, `16` scans each, `Rs 6,550` / `32` = `Rs 204.69` -> **`Rs 205`** rounded avg bill; `2.5`-day mean gap = **`12` visits/month**): **`2 x Rs 205 x 12 = Rs 4,920`** (*historical spend, not guaranteed lift; synthetic ledger*).
- **Simulated 48h Profit Waterfall (`CMP-WINBACK-01`, `Grade B` & `Grade C`):** `12/32` (`37.5%`) vs `1/8` (`12.5%`) -> `(1/8) x 32 = 4` expected organic visits (`Rs 870`) subtracted from `12` (`Rs 2,610`) = **`8` extra visits (`Rs 1,740` extra sales)**. At **assumed `30%` margin (`Grade C`)**: `Rs 522` margin - `Rs 300` cashback = **`+Rs 222.00` before fee**; minus **assumed `5%` promo fee** (`assumption, to verify with Paytm`) on `Rs 2,610` redeemed bills (`Rs 130.50`) = **`+Rs 91.50` after fee** (`Explain Simply` rounds integers to `Rs 92`).

---

## 5. Fallback Chain, Credit Protection & Public Render vs Unlocked Demo

- **Three-Tier Router (`app/providers/router.py`):** **1. Sarvam AI** (`bulbul:v3` TTS, `saaras:v4` STT `<= 10s`, `sarvam-105b-conversations` Chat) -> **2. Groq** (`openai/gpt-oss-20b` Chat, `whisper-large-v3-turbo` STT, `canopylabs/orpheus-v1-english` EN TTS) -> **3. Browser Web Speech + Deterministic SQLite Templates**. Errors/caps fail over silently and log a compact notice in `Technical & Audit View`.
- **Grounding & Credit Guards:** `verify_numeric_grounding` validates ASCII, Devanagari, and Kannada digits against SQLite facts; `PersistentProviderCache` (`data/provider_cache.db`), `10s` mic cap, `60` global / `35` session Sarvam call caps, `30%` credit cap, `30/min` IP rate limit, and `PUBLIC_DEPLOY=true` + constant-time `DEMO_PIN` unlock protect live credits on Render.

---

## 6. Twelve Additional Mentor & Judge Questions

9. **Why frame the problem around customer loss instead of dashboard literacy?**
   Losing `48` repeat evening buyers or `Rs 4,920/month` in delayed regulars is the actual revenue leak; voice in Kannada, Hindi, and English is simply the fastest delivery channel at closing time.
10. **How does a shopkeeper who never opens a dashboard use VyaparVoice?**
    Through spoken closing briefings and `50%`/`80%`/`100%` alerts on the Soundbox speaker plus spoken `Explain Simply` readouts, replying via the Paytm for Business app (`assumption, to verify with Paytm`).
11. **Why show both `+Rs 222` and `+Rs 91.50` (and why does `Explain Simply` say `Rs 92`)?**
    `+Rs 222` is merchant return before any platform fee (at an assumed `30%` margin); `+Rs 91.50` deducts an assumed `5%` promo fee on all `Rs 2,610` redeemed bills (`Rs 130.50`). `Explain Simply` converts all figures to whole rupees (`round(91.5) = 92`) for smoother spoken audio.
12. **What happens if `15` customers arrive on a `Rs 300` (`12`-bill) cap?**
    Passes state *"valid while shop offer budget lasts"*. `BEGIN IMMEDIATE` locks stop cashback at `12` bills (`Rs 300`), set `CAP_PAUSED`, and bill customers `13` to `15` at regular price with zero extra merchant cost.
13. **Can Sarvam or Groq invent a rupee figure or percentage?**
    No. Python computes every number; `verify_numeric_grounding` checks Latin, Devanagari, and Kannada digits and reverts to deterministic SQLite templates if any ungrounded number appears.
14. **Why pair Sarvam primary with Groq secondary?**
    Sarvam provides native Kannada, Hindi, and Indian English TTS/STT plus Indic chat in one stack; Groq provides fast free-tier failover before browser Web Speech + templates.
15. **What happens on stage if Sarvam times out or hits its call limit?**
    `ProviderRouter` fails over automatically in milliseconds to Groq and then to browser Web Speech + SQLite templates without interrupting the merchant screen.
16. **How do you stop public Render visitors from draining API credits?**
    `PUBLIC_DEPLOY=true` blocks live external calls until unlocked in `Technical & Audit View` with `DEMO_PIN` (`hmac.compare_digest`), backed by SQLite caching, `60`/`35` call caps, and `30/min` IP rate limits.
17. **Why does `"Customers today?"` say `25 October 2026`?**
    `ledger_meta.ledger_end_date` records `2026-10-25` (`9` buyers, `Rs 1,750`). Citing *"25 October 2026, the latest day in the sample data"* avoids pretending static data is live calendar traffic.
18. **Are the Hindi and Kannada strings production-ready?**
    No. Both carry `"Draft - unreviewed by native speaker"` badges pending native merchant copy review.
19. **What if a merchant commands `"Give 80 rupees off on 100 rupees to everyone today"`?**
    `evaluate_guardrail_attack` blocks it deterministically before any LLM or database write (`80% > 22%` discount limit, missing consent/cooldown/holdout) and records the block in `audit_logs`.
20. **What are the stop rules for your proposed multi-shop pilot?**
    Run an opt-in `50`-shop darshini pilot (`n = 2,000`, `80/20` holdout) after native language review, and halt immediately if pooled post-fee profit is negative (`95%` lower bound `<= Rs 0`), any cap overruns, or opt-out complaints spike.

---

## 7. One-Page Key Figures Cheat Sheet

| Metric / Component | Exact Value (`v1.5.0`) | Provenance / Label |
| :--- | :--- | :--- |
| **Store & Window** | *Sri Krishna Darshini*, 60d ending `25 Oct 2026` | Synthetic ledger (`seed = 20261025`) |
| **30d QR Sales / Scans** | **`Rs 1,74,685`** (`917` scans in 30d; `1,613` in 60d) | `Grade A` synthetic (`Rs 190` avg bill) |
| **Buyers & Repeat Base** | **`240`** unique; **`175`** repeat (`3+` scans = **`72.9%`**) | `9` buyers (`Rs 1,750`) on `25 Oct 2026` |
| **Briefing Scan Count** | **`111`** UPI payments in closing briefing | `get_voice_briefing()` (`kn` / `hi` / `en`) |
| **Win-Back Funnel** | **`48`** silent -> **`40`** eligible -> **`32` offer / `8` holdout** | `Rs 25` off `Rs 150+`; **`Rs 300` cap** (`12` bills) |
| **Delayed Regulars Risk** | **`Rs 4,920/mo`** = **`2 x Rs 205 x 12`** visits | Historical spend, `possibly after a busy rush` |
| **Dead-Hour Drop** | **`-70%`** (`30` scans at `3 PM` vs `101` at `2 PM`) | `34` of `55` eligible (`Rs 240` cap) |
| **Simulated 48h Return** | **`12/32` (`37.5%`)** vs **`1/8` (`12.5%`)** (`8` extra visits) | Illustrative simulation (`p = 0.2364`, directional) |
| **Simulated 48h Profit** | **`+Rs 222`** pre-fee / **`+Rs 91.50`** post-fee (`Rs 92` rounded) | Assumed `30%` margin & assumed `5%` promo fee |
| **Margin Break-Even** | **`24.7%`** post-fee (`17.2%` pre-fee) at `+25 pp` | Darshinis (`30%`) first; kiranas (`15-20%`) negative |
| **Modelled Monthly Cost** | **`Rs 48/mo` cached** (`Rs 71.80` uncached) | Modelled assumption (`Rs 43` messaging not sent by app) |
| **Soundbox Hardware** | Speaker-based, no mic (to validate with Paytm) | Replies proposed via Paytm app (browser mic in demo) |
| **Providers & Verification** | Sarvam -> Groq -> Browser Speech + Templates | `12` preflight gates, `7` suites (`311` asserts), `21` QA |
