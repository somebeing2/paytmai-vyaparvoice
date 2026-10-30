# Merchant Comprehension and Teach-Back Protocol (docs/TEACH_BACK.md)

Date: 30 October 2026
Component: Task 14 Merchant Copy Comprehension, Ergonomics, and Teach-Back Guide
Review Status:
- English (`en-IN`): `EN author-checked, native review pending`
- Kannada (`kn-IN`): `DRAFT - UNREVIEWED BY NATIVE SPEAKER`
- Hindi (`hi-IN`): `DRAFT - UNREVIEWED BY NATIVE SPEAKER`

---

## 1. Objective

Busy shopkeepers operating a darshini, provision store, or kirana counter at 8:30 PM closing time must understand **exact rupee downside, pass validity rules, and expected outcomes** within 25 seconds without encountering data-science or regulatory jargon.

Every merchant-facing string in `app/templates.py` and `app/engine.py` is enforced at runtime by `app/copy_lint.py` (`assert_valid_merchant_copy`):
- Maximum **34 words per English sentence**.
- **25 banned jargon patterns** blocked automatically (`cohort`, `holdout`, `control group`, `treatment arm`, `p-value`, `Fisher`, `Wilson`, `confidence interval`, `statistically significant`, `underpowered`, `uplift`, `incremental`, `ROI`, `ROAS`, `ARPU`, `DPDP`, `SHA-256`, `opt-in`, `attribution`, `conversion rate`, `anomaly`, `heuristic`, `RFM`, `ITT`, `intention-to-treat`).
- Zero em dashes, zero en dashes, and zero Unicode emojis.

---

## 2. Five-Point Merchant Teach-Back Checklist

Before any pilot merchant activates voice auto-briefings in the 50-shop Bengaluru field study, the field onboarding associate runs this 5-question verbal teach-back check after playing the 8:30 PM Soundbox briefing once:

| # | Teach-Back Question Asked to Merchant | Passing Merchant Answer (Comprehension Target) | UI / Voice Control Supporting It |
| :--- | :--- | :--- | :--- |
| **TB-1** | *"How many regular customers get the 25 rupee offer tonight, and why did 8 others get nothing?"* | *"32 silent regulars get the 25 rupee offer on bills above 150 rupees, and 8 similar regulars get no message so we can compare normal walk-ins."* | Soundbox Briefing + Question Chip: `Why keep 8 without offer?` + `Why?` Drawer |
| **TB-2** | *"If all 32 customers walk in tomorrow, what is the maximum cashback money that can leave your pocket?"* | *"300 rupees maximum (12 paid bills of 25 rupees), unless I raise my spending limit myself."* | Soundbox Briefing + Cap Editor (`Rs 150` to `Rs 2,500`) + Question Chip: `Max loss > Rs 300?` |
| **TB-3** | *"What happens if a 13th customer arrives with the pass after your 300 rupee limit is used up?"* | *"The pass states it is valid while the shop offer budget lasts, so the 13th bill pays normal price without cashback unless I raise my limit beforehand (for example to 400 rupees)."* | Cap-Binding Alert Banner + Question Chip: `13th buyer after cap?` |
| **TB-4** | *"If I say 'Set my spending limit to 400 rupees' out loud, does it change immediately?"* | *"No, Soundbox repeats the new 400 rupee limit and waits for me to say 'Confirm limit' or tap Confirm before changing my budget."* | Two-Step Voice Cap Confirmation (`CAP_CONFIRMATION_PENDING` -> `CAP_CONFIRMED`) |
| **TB-5** | *"After 48 hours, the screen shows 222 rupees profit before fee (91.50 rupees after fee). Is that guaranteed cash or an estimate?"* | *"It is an early estimate on one shop run assuming a 30 percent shop margin, and it needs more shops before treating it as certain."* | Merchant Scorecard Verdict + Visual Evidence Meter + Margin Sensitivity Table |

---

## 3. Noisy-Counter Voice & Screen Ergonomics Built in Stage 2

1. **`Repeat Last` Control:** One-tap button on the Soundbox shell replays the most recent briefing or question answer immediately if street or grinder noise masked a number.
2. **`Slower (0.78x)` Counter Mode:** Toggles speech synthesis and cached audio playback rate down to `0.78x` (with LCD status indicator `8:30 PM IST | 0.78x`) so rupee figures (`25`, `150`, `300`, `400`) are distinct in noisy kitchens.
3. **1-Tap Merchant Question Chips:** Five pre-wired plain-language questions (`Why these 40 buyers?`, `Max loss > Rs 300?`, `13th buyer after cap?`, `Why keep 8 without offer?`, `Why +18L milk?`) answer common merchant doubts without typing prompts.
4. **`Why?` Drawer on Every Card:** Every campaign and stock/service card exposes a single-click `Why?` button showing plain store reasoning in Merchant View and exact SQLite query rules in Technical View.
5. **1-Tap Emergency Stop-Loss:** Live campaigns display an immediate `Emergency Stop-Loss` button (and voice trigger `"Stop offer"`) that halts pass redemptions atomically in SQLite (`PAUSED_STOP_LOSS`).

---

## 4. Native Speaker Review Gate (Pre-Field Requirement)

- Current Kannada (`kn-IN`) and Hindi (`hi-IN`) scripts are deterministic templates marked `DRAFT - UNREVIEWED BY NATIVE SPEAKER`.
- Prior to testing with real Bengaluru shopkeepers, a native Kannada speaker (Indiranagar/Jayanagar retail register) and a native Hindi speaker must verify natural phrasing of pass-budget expiry (`valid while shop offer budget lasts`) and two-step limit confirmation, recording reviewer sign-off in `docs/COPY_REVIEW.md`.
