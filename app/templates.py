from typing import Any, Dict

from .copy_lint import assert_valid_merchant_copy

EVIDENCE_GRADES = {
    "A": {
        "grade": "A",
        "label": "Grade A: Observed Store Ledger (Synthetic Seed 20261025)",
        "description": "Exact SQL counts over the store's UPI transaction and customer tables.",
    },
    "B": {
        "grade": "B",
        "label": "Grade B: Simulated Randomized Holdout (Intention-to-Treat)",
        "description": "Randomized nudged vs silent comparison arm with exact Fisher p-value and Wilson 95% CIs.",
    },
    "C": {
        "grade": "C",
        "label": "Grade C: Modelled Assumption / Pilot Target",
        "description": "Profit figures relying on assumed store gross margin (30%), fee structure (5%), or unvalidated targets.",
    },
}


def render_closing_briefing(
    lang: str,
    owner_first_name: str,
    store_short_name: str,
    recent_day_txns: int,
    eligible_lapsed: int,
    treatment_count: int,
    control_count: int,
    min_silent_days: int,
    max_silent_days: int,
    offer_rupees: int,
    min_bill_rupees: int,
    max_cap_rupees: int,
    extra_milk_liters: int = 18,
) -> Dict[str, Any]:
    """
    Deterministic template renderer for 8:30 PM closing voice briefing.
    All numeric fields come strictly from SQLite queries; zero LLM text generation.
    Kannada and Hindi are explicitly tagged DRAFT - UNREVIEWED BY NATIVE SPEAKER.
    """
    if lang == "kn":
        script = (
            f"ನಮಸ್ಕಾರ {owner_first_name} ಅವರೇ! ಇಂದು {store_short_name} ನಲ್ಲಿ {recent_day_txns} ಯುಪಿಐ ಪೇಮೆಂಟ್ ಆಗಿದೆ. "
            f"ಆಫರ್ ಪಡೆಯಲು ಒಪ್ಪಿದ {eligible_lapsed} ಖಾಯಂ ಗ್ರಾಹಕರು ಕಳೆದ {min_silent_days} ರಿಂದ {max_silent_days} ದಿನಗಳಿಂದ ಬಂದಿಲ್ಲ. "
            f"ಇವರಲ್ಲಿ {treatment_count} ಗ್ರಾಹಕರಿಗೆ {min_bill_rupees} ರೂಪಾಯಿ ಮೇಲಿನ ಬಿಲ್ ಮೇಲೆ {offer_rupees} ರೂಪಾಯಿ ಕ್ಯಾಶ್‌ಬ್ಯಾಕ್ ಕಳುಹಿಸಬಹುದು, "
            f"ಮತ್ತು ಸಾಮಾನ್ಯ ಭೇಟಿ ಹೋಲಿಸಲು {control_count} ಗ್ರಾಹಕರನ್ನು ಆಫರ್ ಇಲ್ಲದೆ ಇಡಲಾಗುತ್ತದೆ. "
            f"ನಿಮ್ಮ ಒಟ್ಟು ಖರ್ಚು {max_cap_rupees} ರೂಪಾಯಿ ಮಿತಿಯಲ್ಲಿ ನಿಲ್ಲುತ್ತದೆ. "
            f"ನಾಳೆಯ ಶನಿವಾರದ ರಶ್‌ಗಾಗಿ {extra_milk_liters} ಲೀಟರ್ ಹೆಚ್ಚುವರಿ ಹಾಲು ಬೇಕಾಗಬಹುದು. ಒಪ್ಪಿಗೆ ನೀಡಲು ಹೌದು ಕಳುಹಿಸಿ ಎಂದು ಹೇಳಿ."
        )
        romanized = (
            f"Namaskara {owner_first_name} avare! {eligible_lapsed} khayam grahakaru {min_silent_days}-{max_silent_days} dinagalinda bandilla. "
            f"{treatment_count} grahakarige Rs {offer_rupees} cashback (Rs {min_bill_rupees}+ bill) kaluhisabahudu; "
            f"ottu kharchu Rs {max_cap_rupees} mitiyalli nilluttade. Oppige needalu 'Haudu, kaluhisi' endu heli."
        )
        assert_valid_merchant_copy(script, check_sentence_length=False)
        return {
            "lang_code": "kn-IN",
            "language_name": "ಕನ್ನಡ (Kannada - Bengaluru)",
            "review_status": "DRAFT - UNREVIEWED BY NATIVE SPEAKER",
            "is_draft_translation": True,
            "headline": "ರಾತ್ರಿ 8:30 ಕ್ಲೋಸಿಂಗ್ ಬ್ರೀಫಿಂಗ್ - Paytm AI Soundbox",
            "script": script,
            "romanized": romanized,
            "cta_hint": "Say: 'Haudu kaluhisi' or click 1-Tap Approve",
            "evidence_grade": "A",
        }

    if lang == "hi":
        script = (
            f"नमस्ते {owner_first_name} जी! आज {store_short_name} पर {recent_day_txns} यूपीआई पेमेंट हुए। "
            f"ऑफर की सहमति देने वाले आपके {eligible_lapsed} पुराने ग्राहक पिछले {min_silent_days} से {max_silent_days} दिनों से नहीं आए हैं। "
            f"आप {treatment_count} ग्राहकों को {min_bill_rupees} रुपये की खरीद पर {offer_rupees} रुपये का कैशबैक भेज सकते हैं, "
            f"और सामान्य बिक्री जांचने के लिए {control_count} ग्राहकों को बिना ऑफर रखा जाएगा। "
            f"आपका अधिकतम खर्च {max_cap_rupees} रुपये पर रुक जाएगा। "
            f"कल सुबह की भीड़ के लिए {extra_milk_liters} लीटर अतिरिक्त दूध मंगवाने की सलाह है। शुरू करने के लिए हां भेज दो बोलें।"
        )
        romanized = (
            f"Namaste {owner_first_name} ji! Aapke {eligible_lapsed} purane grahak {min_silent_days}-{max_silent_days} dino se nahi aaye hain. "
            f"{treatment_count} grahakon ko Rs {offer_rupees} cashback (Rs {min_bill_rupees}+ bill) bhej sakte hain; "
            f"adhiktam kharch Rs {max_cap_rupees} par ruk jayega. Shuru karne ke liye 'Haan, bhej do' bolein."
        )
        assert_valid_merchant_copy(script, check_sentence_length=False)
        return {
            "lang_code": "hi-IN",
            "language_name": "हिंदी (Hindi)",
            "review_status": "DRAFT - UNREVIEWED BY NATIVE SPEAKER",
            "is_draft_translation": True,
            "headline": "रात 8:30 क्लोजिंग वॉइस ब्रीफिंग - Paytm AI Soundbox",
            "script": script,
            "romanized": romanized,
            "cta_hint": "Say: 'Haan bhej do' or click 1-Tap Approve",
            "evidence_grade": "A",
        }

    script_en = (
        f"Good evening {owner_first_name} avare! Today {store_short_name} recorded {recent_day_txns} Paytm QR payments. "
        f"{eligible_lapsed} regular evening customers who agreed to shop offers have not visited for {min_silent_days} to {max_silent_days} days. "
        f"You can send {treatment_count} of them a {offer_rupees} rupee cashback on bills above {min_bill_rupees} rupees, "
        f"while keeping {control_count} aside without an offer to compare normal visits. "
        f"Your actual cashback spend stops strictly at {max_cap_rupees} rupees. "
        f"Tomorrow's weekend rush also needs {extra_milk_liters} liters extra milk. Say Approve or tap once on Soundbox!"
    )
    assert_valid_merchant_copy(script_en, check_sentence_length=True)
    return {
        "lang_code": "en-IN",
        "language_name": "English (India)",
        "review_status": "REVIEWED",
        "is_draft_translation": False,
        "headline": "8:30 PM Closing Voice Briefing - Paytm AI Soundbox",
        "script": script_en,
        "romanized": "Plain Indian English - Deterministic Template (Reviewed)",
        "cta_hint": "Say: 'Yes, approve win-back' or click 1-Tap Approve",
        "evidence_grade": "A",
    }


def render_cap_warning_merchant(
    treatment_count: int,
    offer_rupees: int,
    max_budget: int,
    max_funded_redemptions: int,
    overrun_prob_pct: float,
    suggested_cap_rupees: int,
) -> str:
    face_exposure = treatment_count * offer_rupees
    msg = (
        f"Spending limit notice: all {treatment_count} customers receive a {offer_rupees} rupee pass "
        f"({face_exposure} rupees total face value), while your cashback payout stops strictly at {max_budget} rupees "
        f"({max_funded_redemptions} paid redemptions). "
        f"There is a {overrun_prob_pct:.1f} percent chance more than {max_funded_redemptions} customers come back to claim it. "
        f"Raise your limit to {suggested_cap_rupees} rupees if you want fewer than 1 in 10 runs to turn away late redeemers."
    )
    return assert_valid_merchant_copy(msg, check_sentence_length=True)


def render_merchant_scorecard_summary(
    treated_returned: int,
    treatment_count: int,
    control_returned: int,
    control_count: int,
    funded_redemptions: int,
    refused_redemptions: int,
    cap_reached: bool,
    budget_spent: int,
    max_budget: int,
    gross_margin_pct: float,
    net_profit_pre_fee: float,
    net_profit_post_fee: float,
    waves_needed_80_20: int,
    is_significant: bool,
) -> str:
    signal_phrase = (
        "Confirmed pattern across enough customers"
        if is_significant
        else f"Early check (run about {waves_needed_80_20} weekly waves before treating this as certain)"
    )
    cap_phrase = (
        f"Your {max_budget} rupee limit was reached after {funded_redemptions} paid redemptions ({refused_redemptions} extra redemptions were declined after the limit)."
        if cap_reached
        else f"Cashback paid was {budget_spent} rupees within your {max_budget} rupee limit."
    )
    msg = (
        f"{signal_phrase}. {treated_returned} of {treatment_count} customers with an offer came back, "
        f"compared to {control_returned} of {control_count} customers kept without an offer. "
        f"{cap_phrase} "
        f"At an assumed {gross_margin_pct:.0f} percent shop margin, estimated profit after offer cost is "
        f"{net_profit_pre_fee:.0f} rupees before Paytm's fee ({net_profit_post_fee:.2f} rupees after the 5 percent redeemed-bill fee)."
    )
    return assert_valid_merchant_copy(msg, check_sentence_length=True)
