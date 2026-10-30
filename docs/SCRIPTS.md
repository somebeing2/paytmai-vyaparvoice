# PaytmAI VyaparVoice - Timed Pitch Scripts & Fallback Variants

- **Team Name:** SemiTechnical
- **Member Name:** Kevin Joseph
- **Track:** Track 1 - Merchant Growth AI (Paytm Build for India AI Hackathon, Bengaluru Finals, 31 Oct 2026)
- **Canonical Numbers Source:** `results/slide_numbers.md` and `AUDIT.md`
- **Deck Used:** `deck/v1/PaytmAI_VyaparVoice_v1.pptx` (5 Main Slides + 9 Appendix Slides; upgradeable to `deck/v2/` after Stage 2)

---

## Pre-Pitch Operational Rules

1. **Synthetic Data Transparency:** Always state in the first 30 seconds of any demo or metric discussion that the store ledger (`Sri Krishna Darshini & Provisions, Indiranagar`) is a deterministic 60-day synthetic UPI dataset (`1,613` transactions across `240` unique UPI payer profiles; `917` scans and `Rs 1,74,685` GMV in the last 30 days).
2. **Sarvam AI Honesty Toggle:**
   - **Default Line (Web Speech API / Cached Audio):** *"Today our voice loop runs on deterministic templates with browser speech synthesis, while our keyless Sarvam Bulbul TTS and Saaras STT adapter is mock-verified and gated behind a strict 30 percent credit cap."*
   - **Saturday Swap-In Line (USE ONLY IF `make activate-sarvam` and `make sarvam-selftest` succeeded between 11:00 AM and 1:00 PM):** *"For Kannada and Hindi voice delivery, we are running through Sarvam Bulbul TTS and Saaras STT behind a fail-closed credit ledger capped at 30 percent of our hackathon allocation, with cached audio fallback."*
3. **Statistical Discipline:** Never call the `N = 40` (`32` nudged vs `8` holdout) simulation "statistically proven." State `37.5%` vs `12.5%` (`Fisher exact p = 0.24`), show the 95% Wilson intervals (`22.9%-54.8%` vs `2.2%-47.1%`), and note that `46 to 54` customers per arm are required for 80% statistical power.

---

## Format 1: 60-Second Elevator / Triage Script (~145 words)

**[0:00 - 0:15 | Hook & Problem - Slide 1]**
Good morning. I am Kevin Joseph from Team SemiTechnical, building PaytmAI VyaparVoice for Track 1. Paytm powers `1.57 crore` merchant device subscriptions processing `Rs 7.1 lakh crore` in quarterly GMV, yet Soundbox today is a passive payment speaker. When regular customers quietly stop visiting, a busy counter merchant sees isolated scan alerts, not retention trends, and rarely opens analytics dashboards.

**[0:15 - 0:40 | Product Mechanism - Slide 2 & Live App Glance]**
VyaparVoice turns Soundbox and Paytm for Business into a 20-second 8:30 PM closing voice workflow. On our 60-day synthetic Indiranagar darshini ledger (`1,613` scans, `240` payers), our deterministic SQL engine flags `48` lapsed regulars, filters down to `40` DPDP-consented and 14-day cooldown-eligible buyers, holds back `20%` (`8` buyers) to measure organic returns, and asks the merchant for one voice confirmation before issuing capped UPI QR offers.

**[0:40 - 1:00 | Honest Economics & Close - Slides 4 & 5]**
In simulation at a `30%` store margin, the campaign yields `+Rs 222` net merchant profit pre-fee on `Rs 300` cashback, while cached AI inference costs `Rs 5` per merchant monthly (`Rs 48` total COGS). Even on a pure `Rs 79` SaaS add-on across `5%` of Paytm devices, that is `Rs 74.4 crore` ARR (`Rs 243 crore` full ecosystem base case). Thank you.

---

## Format 2: 3-Minute Round-1 Table Judging Script (~415 words)

**[0:00 - 0:30 | Slide 1 & Slide 2: Real Merchant Bottleneck]**
Hello judges, I am Kevin Joseph, Team SemiTechnical. Paytm has `1.57 crore` device merchants (Q1 FY27), but small food and kirana owners working a counter cannot write prompts or study CRM tables. When repeat buyers drift away or 3-to-5 PM traffic drops `70%` below peak, merchants lose high-margin repeat revenue without noticing. VyaparVoice solves this with a zero-typing 8:30 PM closing voice brief and one-command campaign execution.

**[0:30 - 1:55 | Live Demo: Sri Krishna Darshini & Provisions (Synthetic 60-Day Store)]**
*(Switch to live browser tab; keep Deck Slide 3 ready behind it)*
Let me show the live FastAPI and SQLite MVP running on a synthetic 60-day UPI ledger for Sri Krishna Darshini in Indiranagar (`1,613` total scans across `240` payers; `917` scans and `Rs 1,74,685` GMV in the last 30 days):
1. **8:30 PM Closing Brief:** I click **Play Voice Brief** in English or Kannada. Every figure comes from deterministic SQLite queries and templates rather than an LLM inventing math. It flags `48` lapsed evening regulars (`16 to 38` days silent, median `19` days), a `3 to 5 PM` dead-hour combo opportunity (`CMP-DEADHOUR-02`), and a weekend dairy supplier restock order (`+18L milk`).
2. **Guardrails & Consent Filtering:** Look at `CMP-WINBACK-01`. Out of `48` lapsed regulars, the engine excludes `5` without DPDP marketing consent and `3` inside the 14-day anti-spam cooldown, leaving `40` policy-eligible buyers. It enforces the `<=22%` discount floor (`Rs 25` on `Rs 150+` = `16.7%`), reserves `8` (`20%`) in a silent control group, and prepares `32` nudges under a `Rs 300` merchant cap.
3. **Voice Approval & Settlement:** I give the voice confirmation (`"Haan, bhej do"` / `"Approve"`). Only then does the state move from `PENDING_APPROVAL` to `LIVE_DISPATCHED`. Next, I trigger the deterministic 48-hour settlement simulator (`SIMULATED_48H`) to inspect causal lift.

**[1:55 - 2:35 | Slide 4: Statistical & Profit Honesty]**
*(Switch to Slide 4)*
Here is how we report lift honestly. In simulation, `12 of 32` nudged buyers return (`37.5%`, 95% Wilson CI `22.9% to 54.8%`) versus `1 of 8` holdout (`12.5%`, CI `2.2% to 47.1%`). Because `N = 40` yields Fisher exact `p = 0.24`, we explicitly label single-week store data directional: reaching 80% statistical power requires `46 to 54` buyers per arm, achieved by pooling 4 weekly runs. Crucially, we deduct organic returners and COGS: `8` incremental visits generate `Rs 1,740` incremental sales. At a `30%` store gross margin, that is `Rs 522` gross profit against `Rs 300` cashback, leaving `+Rs 222` net profit pre-fee (`+74%` net ROI), or `+Rs 91.50` after Paytm's `5%` redeemed-bill fee.

**[2:35 - 3:00 | Slide 5: Paytm Scale Economics]**
*(Switch to Slide 5)*
With template caching (`~88%` hit rate), AI voice and SLM cost `Rs 5.00` per shop monthly (`Rs 48.00` total COGS with WhatsApp delivery, `Rs 71.80` uncached). At `5%` adoption (`7.85 lakh` merchants), VyaparVoice generates `Rs 74.4 crore` ARR on the `Rs 79` SaaS add-on alone, `Rs 170.5 crore` excluding credit, and `Rs 243.0 crore` in our full base case. Happy to take your toughest questions.

---

## Format 3: 5-Minute Top-10 Stage Finale Script (~690 words)

**[0:00 - 0:45 | Slide 1: Why Soundbox Must Move From Passive Alerts to Retention]**
Good evening judges. I am Kevin Joseph from Team SemiTechnical, presenting PaytmAI VyaparVoice for Track 1: Merchant Growth AI.
In Q1 FY27, One97 Communications reported `1.57 crore` merchant device subscriptions and `Rs 7.1 lakh crore` in quarterly GMV. Soundbox won the counter because it gave merchants instant trust via audio without touching a screen. Yet once the payment clears, the intelligence stops. When loyal regulars stop visiting a darshini or provisions shop, the owner hears isolated daily alerts, not silent customer churn. Standard analytics dashboards do not fix this because single-counter operators do not export CSVs, write AI prompts, or configure CRM segments during service hours.

**[0:45 - 1:25 | Slide 2: Closed-Loop Voice Retention Architecture]**
*(Advance to Slide 2)*
VyaparVoice closes that gap in 20 seconds at closing time. Each evening at 8:30 PM, a deterministic SQL analytics engine scans hashed UPI payer histories to detect lapsed regulars, afternoon dead-hour troughs, and weekend supply spikes. It delivers a concise closing brief in Kannada, Hindi, or English. Every number is computed in SQLite and rendered through locked templates so no generative model ever touches personal identifiers or invents financial figures. When the merchant says *"Haudu, kaluhisi"* or *"Haan, bhej do"*, the engine enforces DPDP Act 2023 consent, a 14-day anti-spam cooldown, a `<=22%` store margin discount floor, a mandatory `20%` silent control holdout, and a hard commitment-based rupee cap before issuing Paytm QR cashback passes.

**[1:25 - 3:15 | Live Product Walkthrough (1m 50s)]**
*(Switch to live application window)*
Let us walk through our live MVP on a 60-day synthetic dataset representing Sri Krishna Darshini & Provisions in Indiranagar (`1,613` transactions across `240` unique UPI payer profiles; `917` scans and `Rs 1,74,685` GMV over the last 30 days):
- **Step 1 - Multilingual 8:30 PM Brief:** I select Kannada (`kn-IN`) or English (`en-IN`) and play the brief. *[Use Default or Saturday Sarvam Swap-In Line per Rule 2 above.]* Notice the brief states exact database facts: `40` policy-eligible evening regulars (from `48` silent `16 to 38` days, median `19` days), a `3 to 5 PM` dead-hour trough (`30` scans vs `101` peak = `-70%`), and tomorrow's `+18L` milk rush prep.
- **Step 2 - Inspecting the 5 Guardrails (`CMP-WINBACK-01`):** Before any message leaves, the card verifies all five deterministic guardrails: `43/48` DPDP opted-in (`5` excluded), `40/43` clear of the 14-day anti-spam cooldown (`3` excluded), `16.7%` effective discount (`Rs 25` on `Rs 150+`, below the `22%` store cap), `80/20` holdout split (`32` treatment vs `8` silent control), and a strict `Rs 300` merchant budget cap.
- **Step 3 - Voice Intent & Approval Gate:** Nothing fires autonomously. I trigger the voice command *"Yes, approve win-back"*. The deterministic parser transitions `CMP-WINBACK-01` from `PENDING_APPROVAL` to `LIVE_DISPATCHED` and writes an immutable governance audit log.
- **Step 4 - 48-Hour Settlement & Holdout Audit:** Now I click **Simulate 48h QR Redemptions** (`SIMULATED_48H`) to run the seeded settlement ledger and inspect whether the merchant actually made money after product costs.

**[3:15 - 4:15 | Slide 4: Defensible Statistics & Real Merchant Profit]**
*(Switch back to Deck Slide 4)*
We built our evaluation to survive a data-science audit rather than inflate vanity metrics:
- First, **statistical power honesty**: in this single-campaign simulation, `12 of 32` nudged buyers return (`37.5%`, 95% Wilson CI `22.9% to 54.8%`) against `1 of 8` holdout buyers (`12.5%`, CI `2.2% to 47.1%`). Two-sided Fisher exact `p` is `0.24`. At `N = 40`, one campaign is an interim directional signal; achieving 80% power at `alpha = 0.05` requires `46 to 54` buyers per arm, which a store reaches across roughly four weekly runs.
- Second, **real net profit, not gross sales over promo**: `12` returning bills at `Rs 217.50` average equal `Rs 2,610` gross sales, but `4` of those visits (`12.5% x 32`) would have happened organically, meaning `Rs 100` of cashback subsidized baseline traffic. The true incremental sales lift is `8` visits or `Rs 1,740` (`5.8x` gross sales per rupee of cashback). Applying a realistic `30%` store gross margin yields `Rs 522` incremental gross profit (`1.74x` promo spend), leaving **`+Rs 222` net profit pre-fee (`+74%` ROI)** and **`+Rs 91.50` net merchant profit (`+30.5%`)** even after Paytm's `5%` success fee (`Rs 130.50`). Any store above `24.7%` gross margin profits post-fee.

**[4:15 - 5:00 | Slide 5: Unit Economics & Three Transparent ARR Cases]**
*(Advance to Slide 5)*
Finally, does this make money for Paytm without burning inference credits? Because closing briefs follow structured store templates (`~88%` phrase-cache hit rate), monthly AI cost is `Rs 1.80` for SLM intent plus `Rs 3.20` for cached Bulbul v3 TTS, which totals just `Rs 5.00` of AI (`Rs 48.00` total COGS including `Rs 43` WhatsApp delivery; even at `0%` cache hit, COGS is `Rs 71.80`).
Across `5%` of Paytm's `1.57 crore` device base (`7.85 lakh` active merchants), we present three transparent revenue cases:
1. **SaaS-Only Floor (`Rs 79/month`):** `Rs 74.4 crore` ARR (`39.2%` gross margin).
2. **Core Retention (`Rs 181/month`, SaaS + `5%` redeemed-bill fee, zero credit assumptions):** `Rs 170.5 crore` ARR (`73.5%` gross margin).
3. **Full Ecosystem Base Case (`Rs 258/month`, adding verified-cashflow loan referrals):** `Rs 243.0 crore` ARR (`81.4%` cached gross margin).
VyaparVoice turns Paytm's existing Soundbox moat into measurable merchant profit. Thank you.

---

## Format 4: 7-Minute Extended Deep-Dive Script (~930 words)

- **0:00 - 1:00 (Slide 1 + Appendix A2):** Open with One97 Q1 FY27 scale (`1.57 Cr` devices, `Rs 7.1L Cr` GMV, `~7%` Q4 FY26 merchant loan penetration). Contrast payment alerts with silent repeat churn and show the synthetic Indiranagar hourly scan distribution (`3-5 PM` trough at `30` scans vs `101` peak = `-70%`).
- **1:00 - 2:00 (Slide 2 + Appendix A4/A5):** Detail the hybrid architecture: deterministic SQL RFM + anomaly scoring -> locked template generator (zero PII leaves SQLite; banned-jargon lint) -> multilingual voice I/O -> explicit confirmation gate (`PENDING_APPROVAL -> LIVE_DISPATCHED -> SIMULATED_48H`) -> commitment-based cap ledger.
- **2:00 - 4:15 (Live Full-Cycle Demo):**
  1. Run **English** 8:30 PM brief, then switch to **Kannada** (`[DRAFT - UNREVIEWED]` label disclosed) to show instant template rendering.
  2. Walk through both retention campaigns (`CMP-WINBACK-01` lapsed regulars, `CMP-DEADHOUR-02` 3-5 PM filter-coffee combo) and both operational actions (`Smart Dairy Supplier WhatsApp PO` for `+18L milk, +12kg batter`, and `Peak-hour queue delay goodwill recovery`).
  3. Trigger voice approval on `CMP-WINBACK-01`, inspect the immutable governance audit trail (`DPDP consent`, `14-day cooldown`, `<=22% margin floor`, `80/20 control split`, `Rs 300 budget cap`), and run the 48-hour redemption simulator.
  4. Show the Working Capital Readiness view (`Rs 1,74,685` 30-day GMV, `72.9%` repeat payer share, indicative cashflow-backed credit readiness labeled explicitly as an illustrative heuristic rather than a lending underwriting model).
- **4:15 - 5:45 (Slide 4 + Appendix A7):** Walk line-by-line through the causal holdout math (`37.5%` vs `12.5%`, Wilson CIs, `p = 0.24`, `n = 46 to 54` per arm for 80% power) and the merchant profit waterfall (`Rs 2,610` gross returning sales -> minus `Rs 870` organic baseline -> `Rs 1,740` incremental sales -> `Rs 522` gross profit at `30%` margin -> minus `Rs 300` promo -> `+Rs 222` pre-fee / `+Rs 91.50` post-fee; break-even margin `17.2%` pre-fee / `24.7%` post-fee).
- **5:45 - 7:00 (Slide 5 + Appendix A8/A9):** Present COGS (`Rs 48.00` cached vs `Rs 71.80` uncached), the three ARR cases (`Rs 74.4 Cr`, `Rs 170.5 Cr`, `Rs 243.0 Cr`), and the 3-phase rollout starting with a 500-store Bengaluru randomized 4-week holdout pilot to reach `N >= 180` per store cohort and validate causal repeat-visit lift before citywide expansion.

---

## Emergency Deck-Only Fallback Variant (Zero Network / Zero Browser / Audio Failure)

If Wi-Fi drops, localhost fails to render, or stage audio is muted, execute this transition seamlessly without apologizing:

1. **Immediate Bridge Sentence:** *"To keep us strictly on schedule without stage-audio latency, let us walk directly through the exact system state and SQLite audit outputs captured on Slide 3 and Appendix A5."*
2. **Slide 3 Walkthrough (60 seconds):** Point to the four state boxes on Slide 3:
   - Box 1: `917` scans / `Rs 1,74,685` 30d synthetic ledger (`1,613` scans across `240` payers in 60d) -> `48` regulars silent `16-38` days.
   - Box 2: Compliance funnel (`48 -> 43 DPDP opted-in -> 40 14-day cooldown-clear -> 32 treatment / 8 control`).
   - Box 3: Explicit merchant voice gate (`"Haan, bhej do"` / `"Approve"`) and `Rs 300` hard cap.
   - Box 4: 48-hour settlement (`12/32` vs `1/8`) handing straight into Slide 4's profit waterfall.
3. **Static HTML Replay Backup (Post-Stage 3):** Open `static/demo_replay.html` offline if a browser works without Python, or stay inside `PaytmAI_VyaparVoice_v1.pdf` (`Slides 1-5` + `Appendix A5` & `A7`).
