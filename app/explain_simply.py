"""
Task 6: Plain-language 'Explain simply' generator for:
  1. Cap performance
  2. Offer vs non-offer customer comparison (why customers with the offer spent more)
  3. Budget spent vs return
Strictly code-computed numbers, zero jargon ('uplift', 'control group', 'break-even' banned),
strict LLM number-match validator, and zero-key deterministic fallback in en / hi / kn.
"""
import json
import re
from typing import Any, Dict, List, Optional, Set
import httpx

from .config import get_settings
from .copy_lint import BANNED_MERCHANT_JARGON, find_formatting_violations
from .security import assert_paid_calls_permitted

_INDIC_DIGITS = str.maketrans(
    "०१२३४५६७८९೦೧೨೩೪೫೬೭೮೯",
    "01234567890123456789",
)

PLAIN_BANNED_TERMS = list(BANNED_MERCHANT_JARGON) + [
    r"\buplift\b",
    r"\bcontrol\s+group\b",
    r"\bcontrol\s+arm\b",
    r"\bbreak[\s-]*even\b",
    r"\btreatment\b",
    r"\bholdout\b",
    r"\bincremental\b",
    r"\bcohort\b",
    r"\bvariance\b",
    r"\broi\b",
]


def find_plain_jargon_violations(text: str) -> List[str]:
    low = (text or "").lower()
    hits: List[str] = []
    for pat in PLAIN_BANNED_TERMS:
        m = re.search(pat, low)
        if m:
            hits.append(m.group(0))
    return hits


def extract_numbers_normalized(text: str) -> List[str]:
    norm = (text or "").translate(_INDIC_DIGITS)
    norm = re.sub(r"(?<=\d),(?=\d)", "", norm)
    raw = re.findall(r"\d+(?:\.\d+)?", norm)
    cleaned: List[str] = []
    for tok in raw:
        val = float(tok)
        if abs(val - round(val)) < 1e-6:
            cleaned.append(str(int(round(val))))
        else:
            cleaned.append(f"{val:.2f}".rstrip("0").rstrip("."))
    return cleaned


def validate_llm_plain_output(
    candidate_sections: Dict[str, str],
    allowed_numbers: Set[str],
    required_numbers: Set[str],
) -> bool:
    """
    Validate that LLM plain-language text:
      1. Has all 3 non-empty sections,
      2. Contains zero em/en dashes, emojis, or banned jargon ('uplift', 'control group', 'break-even', etc.),
      3. Uses ONLY numbers from allowed_numbers (zero invented or altered numbers),
      4. Preserves all required core numbers.
    """
    for key in ("cap_performance", "customer_comparison", "spend_vs_return"):
        val = (candidate_sections.get(key) or "").strip()
        if not val:
            return False
        if find_formatting_violations(val):
            return False
        if find_plain_jargon_violations(val):
            return False

    combined = " ".join(candidate_sections[k] for k in ("cap_performance", "customer_comparison", "spend_vs_return"))
    found_nums = extract_numbers_normalized(combined)
    if not found_nums:
        return False
    for num_str in found_nums:
        if num_str not in allowed_numbers:
            return False
    found_set = set(found_nums)
    if not required_numbers.issubset(found_set):
        return False
    return True


def compute_plain_facts(cmp_dict: Dict[str, Any]) -> Dict[str, Any]:
    settings = get_settings()
    cap_inr = int(cmp_dict["max_budget"])
    spent_inr = int(cmp_dict["budget_spent"])
    rem_inr = max(0, cap_inr - spent_inr)
    offer_inr = int(cmp_dict["offer_rupees"])
    min_bill_inr = int(cmp_dict["min_bill"])
    paid_bills = int(cmp_dict["funded_redemptions"])
    post_cap_bills = int(cmp_dict["refused_redemptions"])

    t_ret = int(cmp_dict["treatment_returned"])
    t_all = max(1, int(cmp_dict["treatment_count"]))
    c_ret = int(cmp_dict["holdout_returned"])
    c_all = max(1, int(cmp_dict["holdout_count"]))
    gross_sales = int(cmp_dict["gross_treatment_sales"])

    normal_expected = int(round((c_ret / c_all) * t_all))
    extra_buyers = max(0, t_ret - normal_expected)
    avg_bill = int(round(gross_sales / max(1, t_ret))) if t_ret > 0 else 218

    if cmp_dict.get("evaluation") and cmp_dict["evaluation"].get("profit_waterfall"):
        pw = cmp_dict["evaluation"]["profit_waterfall"]
        extra_sales = int(round(float(pw["incremental_sales_inr"])))
        gross_margin_gain = int(round(float(pw["incremental_gross_profit_inr"])))
        profit_before_fee = int(round(float(pw["net_profit_pre_fee_inr"])))
        profit_after_fee = int(round(float(pw["net_profit_post_fee_inr"])))
    else:
        extra_sales = int(round(extra_buyers * avg_bill))
        margin_pct = float(settings.default_gross_margin_pct)
        gross_margin_gain = int(round(extra_sales * (margin_pct / 100.0)))
        profit_before_fee = gross_margin_gain - spent_inr
        paytm_fee = int(round(gross_sales * (float(settings.paytm_promo_fee_pct) / 100.0)))
        profit_after_fee = profit_before_fee - paytm_fee

    has_activity = bool(t_ret > 0 or spent_inr > 0 or cmp_dict.get("status") == "SIMULATED_48H")
    return {
        "campaign_id": cmp_dict["campaign_id"],
        "has_activity": has_activity,
        "cap_inr": cap_inr,
        "spent_inr": spent_inr,
        "remaining_inr": rem_inr,
        "offer_inr": offer_inr,
        "min_bill_inr": min_bill_inr,
        "paid_bills": paid_bills,
        "post_cap_bills": post_cap_bills,
        "offer_buyers_visited": t_ret,
        "offer_buyers_total": t_all,
        "no_offer_buyers_visited": c_ret,
        "no_offer_buyers_total": c_all,
        "normal_expected_buyers": normal_expected,
        "extra_buyers": extra_buyers,
        "avg_bill_inr": avg_bill,
        "extra_sales_inr": extra_sales,
        "margin_pct": int(round(float(settings.default_gross_margin_pct))),
        "gross_margin_gain_inr": gross_margin_gain,
        "profit_before_fee_inr": profit_before_fee,
        "profit_after_fee_inr": profit_after_fee,
    }


def render_static_plain_explanation(facts: Dict[str, Any], lang: str) -> Dict[str, str]:
    lg = lang if lang in ("en", "hi", "kn") else "en"
    f = facts

    if not f["has_activity"]:
        if lg == "hi":
            s1 = (
                f"आपकी अधिकतम छूट सीमा {f['cap_inr']} रुपये तय है और अभी {f['spent_inr']} रुपये खर्च हुए हैं। "
                f"सीमा पूरी होते ही कैशबैक अपने आप रुक जाएगा।"
            )
            s2 = (
                f"{f['offer_buyers_total']} ग्राहकों को {f['min_bill_inr']} रुपये के बिल पर {f['offer_inr']} रुपये की छूट मिलेगी, "
                f"जबकि {f['no_offer_buyers_total']} ग्राहकों को बिना ऑफर रखा गया है ताकि सामान्य दुकानदारी से सीधा फर्क दिखे।"
            )
            s3 = (
                f"अभी ऑफर शुरू नहीं हुआ है इसलिए खर्च {f['spent_inr']} रुपये और मुनाफा {f['profit_before_fee_inr']} रुपये है।"
            )
            return {"cap_performance": s1, "customer_comparison": s2, "spend_vs_return": s3}

        if lg == "kn":
            s1 = (
                f"ನಿಮ್ಮ ಗರಿಷ್ಠ ಆಫರ್ ಮಿತಿ {f['cap_inr']} ರೂಪಾಯಿ ಆಗಿದ್ದು ಈಗ {f['spent_inr']} ರೂಪಾಯಿ ಖರ್ಚಾಗಿದೆ. "
                f"ಮಿತಿ ತಲುಪಿದ ತಕ್ಷಣ ಕ್ಯಾಶ್‌ಬ್ಯಾಕ್ ತಾನಾಗಿಯೇ ನಿಲ್ಲುತ್ತದೆ."
            )
            s2 = (
                f"{f['offer_buyers_total']} ಗ್ರಾಹಕರಿಗೆ {f['min_bill_inr']} ರೂಪಾಯಿ ಬಿಲ್ ಮೇಲೆ {f['offer_inr']} ರೂಪಾಯಿ ರಿಯಾಯಿತಿ ಸಿಗುತ್ತದೆ, "
                f"ಮತ್ತು ಸಾಮಾನ್ಯ ಭೇಟಿ ತಿಳಿಯಲು {f['no_offer_buyers_total']} ಗ್ರಾಹಕರಿಗೆ ಆಫರ್ ನೀಡಿಲ್ಲ."
            )
            s3 = (
                f"ಆಫರ್ ಇನ್ನೂ ಪ್ರಾರಂಭವಾಗಿಲ್ಲದ ಕಾರಣ ಖರ್ಚು {f['spent_inr']} ರೂಪಾಯಿ ಮತ್ತು ಲಾಭ {f['profit_before_fee_inr']} ರೂಪಾಯಿ ಆಗಿದೆ."
            )
            return {"cap_performance": s1, "customer_comparison": s2, "spend_vs_return": s3}

        s1 = (
            f"Your budget cap is set at Rs {f['cap_inr']} with Rs {f['spent_inr']} spent so far. "
            f"Cashback stops automatically once Rs {f['cap_inr']} is used."
        )
        s2 = (
            f"{f['offer_buyers_total']} regulars will get Rs {f['offer_inr']} off on bills of Rs {f['min_bill_inr']} or more, "
            f"while {f['no_offer_buyers_total']} similar regulars get no offer so we can see normal shopping."
        )
        s3 = (
            f"Because the offer has not started yet, spend is Rs {f['spent_inr']} and profit after offer is Rs {f['profit_before_fee_inr']}."
        )
        return {"cap_performance": s1, "customer_comparison": s2, "spend_vs_return": s3}

    # Active or completed wave
    if lg == "hi":
        post_note_hi = (
            f" सीमा के बाद आए {f['post_cap_bills']} ग्राहकों ने बिना छूट सामान्य बिल चुकाया।"
            if f["post_cap_bills"] > 0
            else f" अभी {f['remaining_inr']} रुपये का बजट बाकी है।"
        )
        s1 = (
            f"आपके {f['cap_inr']} रुपये बजट में से {f['spent_inr']} रुपये {f['paid_bills']} बिलों पर उपयोग हुए।{post_note_hi}"
        )
        s2 = (
            f"ऑफर पाने वाले {f['offer_buyers_total']} में से {f['offer_buyers_visited']} ग्राहक दुकान आए, "
            f"जबकि बिना ऑफर वाले {f['no_offer_buyers_total']} में से सिर्फ {f['no_offer_buyers_visited']} आए। "
            f"छूट ने पुराने ग्राहकों को वापस बुलाकर {f['extra_buyers']} अतिरिक्त खरीदारी और {f['extra_sales_inr']} रुपये की ज्यादा बिक्री दिलाई।"
        )
        s3 = (
            f"आपने {f['spent_inr']} रुपये कैशबैक दिया और {f['margin_pct']} प्रतिशत दुकान मार्जिन पर {f['gross_margin_gain_inr']} रुपये कमाए। "
            f"खर्च घटाकर आपकी जेब में शुल्क से पहले {f['profit_before_fee_inr']} रुपये बचे (शुल्क के बाद {f['profit_after_fee_inr']} रुपये)।"
        )
        return {"cap_performance": s1, "customer_comparison": s2, "spend_vs_return": s3}

    if lg == "kn":
        post_note_kn = (
            f" ಮಿತಿ ಮುಗಿದ ನಂತರ ಬಂದ {f['post_cap_bills']} ಗ್ರಾಹಕರು ಸಾಮಾನ್ಯ ಬಿಲ್ ಪಾವತಿಸಿದ್ದಾರೆ."
            if f["post_cap_bills"] > 0
            else f" ಇನ್ನೂ {f['remaining_inr']} ರೂಪಾಯಿ ಬಜೆಟ್ ಉಳಿದಿದೆ."
        )
        s1 = (
            f"ನಿಮ್ಮ {f['cap_inr']} ರೂಪಾಯಿ ಬಜೆಟ್‌ನಲ್ಲಿ {f['paid_bills']} ಬಿಲ್‌ಗಳಿಗೆ {f['spent_inr']} ರೂಪಾಯಿ ಬಳಕೆಯಾಗಿದೆ.{post_note_kn}"
        )
        s2 = (
            f"ಆಫರ್ ಪಡೆದ {f['offer_buyers_total']} ಗ್ರಾಹಕರಲ್ಲಿ {f['offer_buyers_visited']} ಜನ ಅಂಗಡಿಗೆ ಬಂದರು, "
            f"ಆದರೆ ಆಫರ್ ಇಲ್ಲದ {f['no_offer_buyers_total']} ಗ್ರಾಹಕರಲ್ಲಿ ಕೇವಲ {f['no_offer_buyers_visited']} ಜನ ಬಂದರು. "
            f"ಈ ರಿಯಾಯಿತಿಯಿಂದ {f['extra_buyers']} ಹೆಚ್ಚುವರಿ ಭೇಟಿ ಮತ್ತು {f['extra_sales_inr']} ರೂಪಾಯಿ ಹೆಚ್ಚುವರಿ ಮಾರಾಟವಾಯಿತು."
        )
        s3 = (
            f"ನೀವು {f['spent_inr']} ರೂಪಾಯಿ ಕ್ಯಾಶ್‌ಬ್ಯಾಕ್ ನೀಡಿ ಶೇಕಡಾ {f['margin_pct']} ಲಾಭಾಂಶದಲ್ಲಿ {f['gross_margin_gain_inr']} ರೂಪಾಯಿ ಗಳಿಸಿದ್ದೀರಿ. "
            f"ಖರ್ಚು ಕಳೆದು ಶುಲ್ಕಕ್ಕೆ ಮೊದಲು {f['profit_before_fee_inr']} ರೂಪಾಯಿ ನಿವ್ವಳ ಲಾಭ ಉಳಿದಿದೆ (ಶುಲ್ಕದ ನಂತರ {f['profit_after_fee_inr']} ರೂಪಾಯಿ)."
        )
        return {"cap_performance": s1, "customer_comparison": s2, "spend_vs_return": s3}

    post_note_en = (
        f" {f['post_cap_bills']} later customers paid regular price with zero extra cashback."
        if f["post_cap_bills"] > 0
        else f" Rs {f['remaining_inr']} remains inside your cap."
    )
    s1 = (
        f"You spent Rs {f['spent_inr']} out of your Rs {f['cap_inr']} budget across {f['paid_bills']} bills.{post_note_en}"
    )
    s2 = (
        f"{f['offer_buyers_visited']} out of {f['offer_buyers_total']} customers who got the offer came to buy, "
        f"compared with {f['no_offer_buyers_visited']} out of {f['no_offer_buyers_total']} who got no offer. "
        f"The Rs {f['offer_inr']} reward nudged silent regulars back, adding {f['extra_buyers']} extra visits and Rs {f['extra_sales_inr']} in extra sales."
    )
    s3 = (
        f"You spent Rs {f['spent_inr']} on cashback and earned Rs {f['gross_margin_gain_inr']} shop margin at {f['margin_pct']} percent. "
        f"That leaves Rs {f['profit_before_fee_inr']} profit before fee, or Rs {f['profit_after_fee_inr']} after fee."
    )
    return {"cap_performance": s1, "customer_comparison": s2, "spend_vs_return": s3}


def _try_llm_plain_explanation(
    facts: Dict[str, Any],
    lang: str,
    allowed_numbers: Set[str],
    required_numbers: Set[str],
) -> Optional[Dict[str, str]]:
    settings = get_settings()
    try:
        assert_paid_calls_permitted("Groq Explain Simply")
    except PermissionError:
        return None
    if not settings.groq_live_allowed:
        return None

    lang_name = "Hindi" if lang == "hi" else ("Kannada" if lang == "kn" else "simple Indian English")
    sys_prompt = (
        f"Write 3 short everyday sentences in {lang_name} as JSON keys "
        '{"cap_performance": "...", "customer_comparison": "...", "spend_vs_return": "..."}. '
        "NEVER use jargon ('uplift', 'control group', 'break-even', 'treatment', 'holdout', 'incremental', 'ROI' are strictly forbidden). "
        "NEVER invent, round, or change any number; copy numbers verbatim from FACTS."
    )
    try:
        with httpx.Client(timeout=4.5) as client:
            resp = client.post(
                f"{settings.groq_base_url}/chat/completions",
                headers={"Authorization": f"Bearer {settings.groq_api_key}", "Content-Type": "application/json"},
                json={
                    "model": settings.groq_model,
                    "temperature": 0.0,
                    "max_tokens": 260,
                    "messages": [
                        {"role": "system", "content": sys_prompt},
                        {"role": "user", "content": f"FACTS: {json.dumps(facts)}"},
                    ],
                },
            )
        if resp.status_code != 200:
            return None
        raw = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "")
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if not m:
            return None
        parsed = json.loads(m.group(0))
        if validate_llm_plain_output(parsed, allowed_numbers=allowed_numbers, required_numbers=required_numbers):
            return {
                "cap_performance": parsed["cap_performance"].strip(),
                "customer_comparison": parsed["customer_comparison"].strip(),
                "spend_vs_return": parsed["spend_vs_return"].strip(),
            }
    except Exception:
        return None
    return None


def generate_plain_explanation(cmp_dict: Dict[str, Any], lang: str = "en") -> Dict[str, Any]:
    lg = lang if lang in ("en", "hi", "kn") else "en"
    facts = compute_plain_facts(cmp_dict)

    allowed_numbers: Set[str] = {
        str(abs(int(v)))
        for k, v in facts.items()
        if isinstance(v, int) and not isinstance(v, bool)
    }
    required_numbers: Set[str] = {
        str(abs(facts["cap_inr"])),
        str(abs(facts["spent_inr"])),
        str(abs(facts["offer_buyers_visited"])) if facts["has_activity"] else str(abs(facts["offer_buyers_total"])),
        str(abs(facts["profit_before_fee_inr"])),
    }

    llm_sections = _try_llm_plain_explanation(
        facts=facts,
        lang=lg,
        allowed_numbers=allowed_numbers,
        required_numbers=required_numbers,
    )
    if llm_sections is not None:
        sections = llm_sections
        provider_used = "groq_number_verified"
    else:
        sections = render_static_plain_explanation(facts, lg)
        provider_used = "deterministic_template"

    # Final safety assertion even on static templates: zero banned jargon & zero formatting violations
    for sec_txt in sections.values():
        assert not find_formatting_violations(sec_txt), f"Formatting violation in plain explanation: {sec_txt}"
        assert not find_plain_jargon_violations(sec_txt), f"Jargon violation in plain explanation: {sec_txt}"

    combined = f"{sections['cap_performance']} {sections['customer_comparison']} {sections['spend_vs_return']}"
    return {
        "campaign_id": facts["campaign_id"],
        "lang": lg,
        "review_status": "Draft - unreviewed by native speaker" if lg in ("hi", "kn") else "EN author-checked, native review pending",
        "provider": provider_used,
        "facts": facts,
        "sections": sections,
        "combined_script": combined,
    }
