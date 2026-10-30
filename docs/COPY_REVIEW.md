# PaytmAI VyaparVoice - Merchant Copy Inventory, Jargon Rules & Native Review Protocol

- **Team Name:** SemiTechnical (`Kevin Joseph`)
- **Purpose:** Canonical audit of all merchant-facing text and spoken prompts in English (`en-IN`), Kannada (`kn-IN`), and Hindi (`hi-IN`), enforcing deterministic template safety, plain-language comprehension, and honest translation status.

---

## 1. Translation & Copy Review Status Disclosure

| Language Code | Language | Generation Method | Current Review Status | Pilot Gate Requirement |
| :--- | :--- | :--- | :--- | :--- |
| **`en-IN`** | Indian English | Deterministic Python string template | **`EN author-checked, native review pending`** (`Kevin Joseph`) | Pass banned-jargon lint + 3-merchant counter teach-back test before live store use |
| **`kn-IN`** | Kannada | Deterministic Python string template | **`[DRAFT - UNREVIEWED BY NATIVE SPEAKER]`** | Must pass 3-merchant native Kannada teach-back test before live store use |
| **`hi-IN`** | Hindi | Deterministic Python string template | **`[DRAFT - UNREVIEWED BY NATIVE SPEAKER]`** | Must pass 3-merchant native Hindi teach-back test before live store use |

> **Strict Honesty Rule:** Neither the application UI, slides, nor spoken pitch may claim that English, Kannada, or Hindi copy has completed merchant field testing until Section 4's counter teach-back protocol is signed off. In the UI, `en-IN` displays `EN author-checked, native review pending`, while `kn-IN` and `hi-IN` display `[DRAFT - UNREVIEWED BY NATIVE SPEAKER]`.

---

## 2. Banned Statistical & Technical Jargon List (Merchant-Facing Copy)

Counter merchants need clear rupee amounts, customer counts, and time windows rather than data-science terminology. Our automated copy linter (`app/copy_lint.py`) rejects any merchant-facing brief, card title, voice prompt, or merchant scorecard containing these terms:

| Banned Term (Case-Insensitive) | Required Plain-Language Replacement for Merchants |
| :--- | :--- |
| `cohort` | `regular customers` / `group of buyers` |
| `holdout` / `control group` / `treatment arm` | `8 customers kept aside without an offer to compare normal visits` |
| `p-value` / `fisher` / `wilson` / `confidence interval` | `early check on one store wave (pool multiple shops to be sure)` or `confirmed result` |
| `statistically significant` / `underpowered` | `confirmed pattern` / `early check (too few customers in one wave to be certain)` |
| `uplift` / `incremental` | `extra visits` / `extra sales above normal` |
| `ROI` / `ROAS` / `ARPU` | `estimated profit after offer cost` |
| `DPDP` / `SHA-256` / `opt-in` | `customers who agreed to receive shop offers` |
| `attribution` / `conversion rate` / `ITT` | `customers who came back and paid by QR` |
| `anomaly` / `heuristic` / `RFM` | `slow afternoon hours` / `regular customers` |

*(Full statistical metrics, including Fisher exact `p`, Wilson 95% CIs, Intention-to-Treat denominators, cap-overrun binomial probabilities, and DPDP audit logs, remain accessible in **Technical & Audit View**.)*

---

## 3. Canonical Deterministic Templates (Variables Injected from SQLite Only)

Every `{variable}` below is populated exclusively from typed Python integers/floats returned by `app/database.py` and `app/engine.py`. No LLM may generate or alter numbers inside these strings.

### 3.1 8:30 PM Closing Voice Brief

- **`en-IN` (`EN author-checked, native review pending`):**
  > `"Good evening {owner_first_name} avare! Today {store_short_name} recorded {recent_day_txns} Paytm QR payments. {eligible_lapsed} regular evening customers who agreed to shop offers have not visited for {min_silent_days} to {max_silent_days} days. You can send {treatment_count} of them a {offer_rupees} rupee cashback on bills above {min_bill_rupees} rupees, while keeping {control_count} aside without an offer to compare normal visits. Your actual cashback spend stops strictly at {max_cap_rupees} rupees. Tomorrow's weekend rush also needs {extra_milk_liters} liters extra milk. Say Approve or tap once on Soundbox!"`

- **`kn-IN` (`[DRAFT - UNREVIEWED BY NATIVE SPEAKER]`):**
  > `"ನಮಸ್ಕಾರ {owner_first_name} ಅವರೇ! ಇಂದು {store_short_name} ನಲ್ಲಿ {recent_day_txns} ಯುಪಿಐ ಪೇಮೆಂಟ್ ಆಗಿದೆ. ಆಫರ್ ಪಡೆಯಲು ಒಪ್ಪಿದ {eligible_lapsed} ಖಾಯಂ ಗ್ರಾಹಕರು ಕಳೆದ {min_silent_days} ರಿಂದ {max_silent_days} ದಿನಗಳಿಂದ ಬಂದಿಲ್ಲ. ಇವರಲ್ಲಿ {treatment_count} ಗ್ರಾಹಕರಿಗೆ {min_bill_rupees} ರೂಪಾಯಿ ಮೇಲಿನ ಬಿಲ್ ಮೇಲೆ {offer_rupees} ರೂಪಾಯಿ ಕ್ಯಾಶ್‌ಬ್ಯಾಕ್ ಕಳುಹಿಸಬಹುದು, ಮತ್ತು ಸಾಮಾನ್ಯ ಭೇಟಿ ಹೋಲಿಸಲು {control_count} ಗ್ರಾಹಕರನ್ನು ಆಫರ್ ಇಲ್ಲದೆ ಇಡಲಾಗುತ್ತದೆ. ನಿಮ್ಮ ಒಟ್ಟು ಖರ್ಚು {max_cap_rupees} ರೂಪಾಯಿ ಮಿತಿಯಲ್ಲಿ ನಿಲ್ಲುತ್ತದೆ. ನಾಳೆಯ ಶನಿವಾರದ ರಶ್‌ಗಾಗಿ {extra_milk_liters} ಲೀಟರ್ ಹೆಚ್ಚುವರಿ ಹಾಲು ಬೇಕಾಗಬಹುದು. ಒಪ್ಪಿಗೆ ನೀಡಲು ಹೌದು ಕಳುಹಿಸಿ ಎಂದು ಹೇಳಿ."`

- **`hi-IN` (`[DRAFT - UNREVIEWED BY NATIVE SPEAKER]`):**
  > `"नमस्ते {owner_first_name} जी! आज {store_short_name} पर {recent_day_txns} यूपीआई पेमेंट हुए। ऑफर की सहमति देने वाले आपके {eligible_lapsed} पुराने ग्राहक पिछले {min_silent_days} से {max_silent_days} दिनों से नहीं आए हैं। आप {treatment_count} ग्राहकों को {min_bill_rupees} रुपये की खरीद पर {offer_rupees} रुपये का कैशबैक भेज सकते हैं, और सामान्य बिक्री जांचने के लिए {control_count} ग्राहकों को बिना ऑफर रखा जाएगा। आपका अधिकतम खर्च {max_cap_rupees} रुपये पर रुक जाएगा। कल सुबह की भीड़ के लिए {extra_milk_liters} लीटर अतिरिक्त दूध मंगवाने की सलाह है। शुरू करने के लिए हां भेज दो बोलें।"`

### 3.2 Customer Pass Terms & Cap Stop Disclosure

- **Customer Pass Terms (`en-IN`, `EN author-checked, native review pending`):**
  > `"Rs {offer_rupees} Paytm QR cashback on your next bill of Rs {min_bill_rupees}+ at {store_short_name}. Valid for 48 hours while the shop's campaign offer budget lasts."`
- **Post-48h Merchant Outcome Scorecard (`en-IN`, `EN author-checked, native review pending`):**
  > `"Early check on one store wave (pool multiple shops before treating this as certain). {treated_returned} of {treatment_count} customers with an offer came back, compared to {control_returned} of {control_count} customers kept without an offer. Your {max_budget} rupee limit was reached after {funded_redemptions} paid redemptions ({refused_redemptions} extra redemptions were declined after the limit). At an assumed {gross_margin_pct} percent shop margin, estimated profit after offer cost is {net_profit_pre_fee} rupees before Paytm's fee ({net_profit_post_fee} rupees after the 5 percent redeemed-bill fee)."`

---

## 4. Counter Merchant Teach-Back Protocol (Required Before Field Pilot)

Before removing `native review pending` / `DRAFT - UNREVIEWED` status on `en-IN`, `kn-IN`, or `hi-IN`:

1. Play the 20-second voice brief once at normal speaking speed to **3 independent counter merchants** (darshini / kirana / pharmacy) per language without showing them the screen.
2. Ask three teach-back questions immediately after playback:
   - **Q1 (Comprehension of Problem):** *"How many regular customers stopped visiting recently?"* (Pass criterion: states `40` eligible or `48` total).
   - **Q2 (Comprehension of Max Liability & Pass Cap):** *"If all 32 customers get a pass, what is the maximum rupee amount that can leave your pocket, and what happens after 12 people redeem?"* (Pass criterion: states `Rs 300` hard stop and knows late redemptions stop unless topped up).
   - **Q3 (Comprehension of Control / Reversibility):** *"Did the offer already go out automatically, or do you have to approve it?"* (Pass criterion: knows it waits for explicit approval and can be skipped or cancelled).
3. Any prompt where `< 3/3` merchants answer Q2 and Q3 accurately must be rewritten in simpler colloquial phrasing and re-tested.
