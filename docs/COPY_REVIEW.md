# PaytmAI VyaparVoice - Merchant Copy Inventory, Jargon Rules & Native Review Protocol

- **Team Name:** SemiTechnical (`Kevin Joseph`)
- **Purpose:** Canonical audit of all merchant-facing text and spoken prompts in English (`en-IN`), Kannada (`kn-IN`), and Hindi (`hi-IN`), enforcing deterministic template safety, plain-language comprehension, and honest translation status.

---

## 1. Translation Review Status Disclosure

| Language Code | Language | Generation Method | Current Review Status | Pilot Gate Requirement |
| :--- | :--- | :--- | :--- | :--- |
| **`en-IN`** | Indian English | Deterministic Python string template | **Reviewed** (`Kevin Joseph`) | Pass banned-jargon automated lint |
| **`kn-IN`** | Kannada | Deterministic Python string template | **`[DRAFT - UNREVIEWED BY NATIVE SPEAKER]`** | Must pass 3-merchant native Kannada teach-back test before live store use |
| **`hi-IN`** | Hindi | Deterministic Python string template | **`[DRAFT - UNREVIEWED BY NATIVE SPEAKER]`** | Must pass 3-merchant native Hindi teach-back test before live store use |

> **Strict Honesty Rule:** Neither the application UI nor the pitch may claim that Kannada or Hindi copy has been field-tested with merchants until Section 4's teach-back table is signed off by native speakers. In the UI, `kn-IN` and `hi-IN` audio/text panels display a visible `Draft copy (pending native review)` badge in Stage 1.

---

## 2. Banned Statistical & Technical Jargon List (Merchant-Facing Copy)

Counter merchants need clear rupee amounts, customer counts, and time windows rather than data-science terminology. Our Stage 1 automated copy linter rejects any merchant-facing brief, card title, voice prompt, or merchant scorecard containing these terms:

| Banned Term (Case-Insensitive) | Required Plain-Language Replacement for Merchants |
| :--- | :--- |
| `cohort` | `regular customers` / `group of buyers` |
| `holdout` / `control group` / `treatment arm` | `8 customers kept aside without an offer to compare normal visits` |
| `p-value` / `fisher` / `wilson` / `confidence interval` | `early signal (needs 3 more weeks of data to be sure)` or `confirmed result` |
| `statistically significant` / `underpowered` | `confirmed pattern` / `early check (too few customers yet to be certain)` |
| `uplift` / `incremental` | `extra visits` / `extra sales above normal` |
| `ROI` / `ROAS` / `ARPU` | `estimated profit after offer cost` |
| `DPDP` / `SHA-256` / `opt-in` | `customers who agreed to receive shop offers` |
| `attribution` / `conversion rate` | `customers who came back and paid by QR` |
| `anomaly` / `heuristic` | `slow afternoon hours` / `busy rush hours` |

*(Note: Full statistical metrics, including Fisher exact `p`, Wilson 95% CIs, holdout split, and DPDP audit logs, remain visible in the collapsible **Audit & Evaluation Drawer** intended for judges, analysts, and Paytm operators.)*

---

## 3. Canonical Deterministic Templates (Variables Injected from SQLite Only)

Every `{variable}` below is populated exclusively from typed Python integers/floats returned by `app/database.py` and `app/engine.py`. No LLM may generate or alter numbers inside these strings.

### 3.1 8:30 PM Closing Voice Brief (`3` Deterministic Findings)

- **`en-IN` (Reviewed):**
  > `"Good evening {owner_first_name} avare. Today your shop recorded {today_txns} Paytm QR payments worth {today_gmv_rs} rupees. Three updates for tonight: First, {lapsed_eligible_count} regular customers who agreed to shop offers have not visited for {min_silent_days} to {max_silent_days} days. You can send {treatment_count} of them a {offer_rs}-rupee return offer on bills above {min_bill_rs} rupees within a strict {cap_rs}-rupee spending limit, while keeping {control_count} aside without an offer to compare normal visits. Second, afternoon sales between 3 PM and 5 PM are 70 percent slower than peak hour. Third, tomorrow's weekend rush needs {extra_milk_liters} liters extra milk. Say 'Approve' to start within your {cap_rs}-rupee limit."`

- **`kn-IN` (`[DRAFT - UNREVIEWED BY NATIVE SPEAKER]`):**
  > `"ನಮಸ್ಕಾರ {owner_first_name} ಅವರೇ. ನಿನ್ನೆ ನಿಮ್ಮ ಅಂಗಡಿಯಲ್ಲಿ {yesterday_txns} ಪೇಟಿಎಂ ಕ್ಯೂಆರ್ ಪೇಮೆಂಟ್ ಮೂಲಕ {yesterday_gmv_rs} ರೂಪಾಯಿ ವ್ಯಾಪಾರ ಆಗಿದೆ. ಇಂದಿನ ಮೂರು ಪ್ರಮುಖ ಮಾಹಿತಿಗಳು: ಮೊದಲನೆಯದಾಗಿ, ಆಫರ್ ಪಡೆಯಲು ಒಪ್ಪಿಗೆ ನೀಡಿದ {lapsed_eligible_count} ಖಾಯಂ ಗ್ರಾಹಕರು ಕಳೆದ {min_silent_days} ರಿಂದ {max_silent_days} ದಿನಗಳಿಂದ ಬಂದಿಲ್ಲ. ನಿಮ್ಮ ಗರಿಷ್ಠ {cap_rs} ರೂಪಾಯಿ ಮಿತಿಯೊಳಗೆ {treatment_count} ಗ್ರಾಹಕರಿಗೆ {offer_rs} ರೂಪಾಯಿ ಕ್ಯಾಶ್‌ಬ್ಯಾಕ್ ಕಳುಹಿಸಬಹುದು; ಸಾಮಾನ್ಯ ಭೇಟಿ ಹೋಲಿಸಲು {control_count} ಗ್ರಾಹಕರಿಗೆ ಆಫರ್ ಕಳುಹಿಸುವುದಿಲ್ಲ. ಎರಡನೆಯದಾಗಿ, ಮಧ್ಯಾಹ್ನ 3 ರಿಂದ 5 ಗಂಟೆಯ ವ್ಯಾಪಾರ ಊಟದ ಸಮಯಕ್ಕಿಂತ ಶೇಕಡಾ 70 ರಷ್ಟು ಕಡಿಮೆ ಇದೆ. ಮೂರನೆಯದಾಗಿ, ಶನಿವಾರ ಬೆಳಿಗ್ಗೆ ಹೆಚ್ಚಿನ ಗ್ರಾಹಕರು ಬರುವ ನಿರೀಕ್ಷೆಯಿದೆ, ದಯವಿಟ್ಟು {top_stock_items} ಸ್ಟಾಕ್ ಪರಿಶೀಲಿಸಿ. {cap_rs} ರೂಪಾಯಿ ಮಿತಿಯಲ್ಲಿ ಆಫರ್ ಕಳುಹಿಸಲು 'ಹೌದು, ಕಳುಹಿಸಿ' ಎಂದು ಹೇಳಿ."`

- **`hi-IN` (`[DRAFT - UNREVIEWED BY NATIVE SPEAKER]`):**
  > `"नमस्कार {owner_first_name} जी। कल आपकी दुकान पर {yesterday_txns} पेटीएम क्यूआर पेमेंट से {yesterday_gmv_rs} रुपये की बिक्री हुई। आज के लिए तीन ज़रूरी बातें: पहली, ऑफर पाने की सहमति देने वाले {lapsed_eligible_count} पुराने ग्राहक {min_silent_days} से {max_silent_days} दिनों से दुकान पर नहीं आए हैं। आप अपने {cap_rs} रुपये के अधिकतम बजट के अंदर {treatment_count} ग्राहकों को {offer_rs} रुपये का ऑफर भेज सकते हैं, और सामान्य बिक्री जांचने के लिए {control_count} ग्राहकों को बिना ऑफर रख सकते हैं। दूसरी, दोपहर 3 से 5 बजे की बिक्री लंच के मुकाबले 70 प्रतिशत कम है। तीसरी, शनिवार सुबह भीड़ रहने का अनुमान है, कृपया {top_stock_items} का स्टॉक जांच लें। {cap_rs} रुपये की सीमा में ऑफर भेजने के लिए 'हां, भेजो' कहें।"`

### 3.2 Pre-Execution Cap Confirmation Readback

- **`en-IN` (Reviewed):**
  > `"Confirmed: sending up to {max_active_passes} active {offer_rs}-rupee QR offers to regular customers. Your total cashback cost will never cross {cap_rs} rupees. Say 'Cancel' within 10 seconds to stop."`
- **`kn-IN` (`[DRAFT - UNREVIEWED BY NATIVE SPEAKER]`):**
  > `"ದೃಢೀಕರಿಸಲಾಗಿದೆ: ಖಾಯಂ ಗ್ರಾಹಕರಿಗೆ ಗರಿಷ್ಠ {max_active_passes} ಸಕ್ರಿಯ {offer_rs}-ರೂಪಾಯಿ ಕ್ಯೂಆರ್ ಆಫರ್ ಕಳುಹಿಸಲಾಗುತ್ತಿದೆ. ನಿಮ್ಮ ಒಟ್ಟು ಕ್ಯಾಶ್‌ಬ್ಯಾಕ್ ಖರ್ಚು {cap_rs} ರೂಪಾಯಿ ಮೀರುವುದಿಲ್ಲ. ನಿಲ್ಲಿಸಲು 10 ಸೆಕೆಂಡ್ ಒಳಗೆ 'ಬೇಡ' ಎಂದು ಹೇಳಿ."`
- **`hi-IN` (`[DRAFT - UNREVIEWED BY NATIVE SPEAKER]`):**
  > `"पुष्टि हो गई: पुराने ग्राहकों को अधिकतम {max_active_passes} सक्रिय {offer_rs}-रुपये के क्यूआर ऑफर भेजे जा रहे हैं। आपका कुल कैशबैक खर्च कभी भी {cap_rs} रुपये से ज़्यादा नहीं होगा। रोकने के लिए 10 सेकंड में 'रद्द करें' कहें।"`

### 3.3 Post-48h Merchant Outcome Scorecard (Plain Language)

- **`en-IN` (Reviewed):**
  > `"48-hour check (early signal, needs 3 more weekly runs to confirm): {treated_returned} of {treatment_count} customers with offers came back, compared to {control_returned} of {control_count} without offers. After subtracting normal visits, {offer_cost_rs} rupees in cashback, and an estimated {margin_pct} percent shop margin, your estimated profit before Paytm fee is {net_profit_pre_fee_rs} rupees ({net_profit_post_fee_rs} rupees after fee)."`

---

## 4. Native-Speaker Teach-Back Protocol (Required Before Field Pilot)

Before removing the `[DRAFT - UNREVIEWED]` badge on `kn-IN` or `hi-IN`:

1. Play the 20-second voice brief once at normal speaking speed to **3 independent counter merchants** (darshini / kirana / pharmacy) who primarily operate in Kannada (`kn-IN`) or Hindi (`hi-IN`), without showing them the screen.
2. Ask three teach-back questions immediately after playback:
   - **Q1 (Comprehension of Problem):** *"How many regular customers stopped visiting recently?"* (Pass criterion: states exact count `40` or `48`).
   - **Q2 (Comprehension of Max Liability):** *"If everyone uses this offer, what is the maximum rupee amount that can come out of your pocket?"* (Pass criterion: states `Rs 300` without hesitation).
   - **Q3 (Comprehension of Control / Reversibility):** *"Did the offer already go out automatically, or do you have to approve it?"* (Pass criterion: knows it waits for explicit approval and can be skipped).
3. Any prompt where `< 3/3` merchants answer Q2 and Q3 accurately must be rewritten in simpler colloquial phrasing and re-tested.
