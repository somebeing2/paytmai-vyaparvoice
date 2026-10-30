import math
import random
from typing import Any, Dict, List, Tuple


def _inv_norm_cdf(p: float) -> float:
    """
    Acklam rational approximation to the standard normal quantile function.
    Relative error < 1.15e-9 across (0, 1).
    """
    if not (0.0 < p < 1.0):
        raise ValueError("Probability p must lie strictly inside (0, 1).")

    a = [
        -3.969683028665376e01,
        2.209460984245205e02,
        -2.759285104469687e02,
        1.383577518672690e02,
        -3.066479806614716e01,
        2.506628277459239e00,
    ]
    b = [
        -5.447609879822406e01,
        1.615858368580409e02,
        -1.556989798598866e02,
        6.680131188771972e01,
        -1.328068155288572e01,
    ]
    c = [
        -7.784894002430293e-03,
        -3.223964580411365e-01,
        -2.400758277161838e00,
        -2.549732539343734e00,
        4.374664141464968e00,
        2.938163982698783e00,
    ]
    d = [
        7.784695709041462e-03,
        3.224671290700398e-01,
        2.445134137142996e00,
        3.754408661907416e00,
    ]

    p_low = 0.02425
    p_high = 1.0 - p_low

    if p < p_low:
        q = math.sqrt(-2.0 * math.log(p))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
            ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0)
        )
    if p <= p_high:
        q = p - 0.5
        r = q * q
        return (
            (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5])
            * q
            / (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1.0)
        )
    q = math.sqrt(-2.0 * math.log(1.0 - p))
    return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
        ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0)
    )


def wilson_ci_95(successes: int, total: int, alpha: float = 0.05) -> Tuple[float, float]:
    """Return exact Wilson score (1 - alpha) confidence interval in percentage points [0, 100]."""
    if total <= 0:
        return (0.0, 0.0)
    z = _inv_norm_cdf(1.0 - alpha / 2.0)
    phat = successes / total
    z2 = z * z
    denom = 1.0 + z2 / total
    center = (phat + z2 / (2.0 * total)) / denom
    half = (z / denom) * math.sqrt((phat * (1.0 - phat) / total) + (z2 / (4.0 * total * total)))
    lo = max(0.0, (center - half) * 100.0)
    hi = min(100.0, (center + half) * 100.0)
    return (round(lo, 2), round(hi, 2))


def fisher_exact_2x2(
    treat_returned: int,
    treat_not_returned: int,
    ctrl_returned: int,
    ctrl_not_returned: int,
) -> Dict[str, float]:
    """
    Exact hypergeometric Fisher test on a 2x2 contingency table.
    Returns both two-sided (minimum-likelihood method matching scipy.stats.fisher_exact)
    and one-sided greater (treatment > control) p-values.
    """
    n_t = treat_returned + treat_not_returned
    n_c = ctrl_returned + ctrl_not_returned
    k_tot = treat_returned + ctrl_returned
    n_tot = n_t + n_c
    if n_tot == 0:
        return {"p_two_sided": 1.0, "p_one_sided_greater": 1.0}

    min_x = max(0, k_tot - n_c)
    max_x = min(n_t, k_tot)
    denom = math.comb(n_tot, k_tot)

    def prob(x: int) -> float:
        return (math.comb(n_t, x) * math.comb(n_c, k_tot - x)) / denom

    p_obs = prob(treat_returned)
    tol = p_obs * (1.0 + 1e-12)

    p_two = sum(prob(x) for x in range(min_x, max_x + 1) if prob(x) <= tol)
    p_greater = sum(prob(x) for x in range(treat_returned, max_x + 1))

    return {
        "p_two_sided": round(min(1.0, p_two), 6),
        "p_one_sided_greater": round(min(1.0, p_greater), 6),
    }


def required_sample_size_two_prop(
    p_control: float,
    p_treatment: float,
    alpha: float = 0.05,
    power: float = 0.80,
    allocation_ratio: float = 1.0,
    continuity_correction: bool = False,
    eligible_per_wave: int = 40,
) -> Dict[str, Any]:
    """
    Two-sided two-proportion sample size calculator supporting unequal allocation
    ratio r = n_treatment / n_control (Fleiss normal method).
    At p_control=0.125, p_treatment=0.375, alpha=0.05, power=0.80:
      - allocation_ratio=1.0 (50/50): 46 control + 46 treatment = 92 total
      - allocation_ratio=4.0 (80/20): 31 control + 124 treatment = 155 total (~4 waves of 40)
    """
    if not (0.0 < p_control < 1.0 and 0.0 < p_treatment < 1.0):
        raise ValueError("Proportions must lie strictly inside (0, 1).")
    if abs(p_treatment - p_control) < 1e-9:
        raise ValueError("Treatment and control proportions must differ.")
    if allocation_ratio <= 0:
        raise ValueError("allocation_ratio must be positive.")

    r = float(allocation_ratio)
    diff = abs(p_treatment - p_control)
    z_alpha = _inv_norm_cdf(1.0 - alpha / 2.0)
    z_beta = _inv_norm_cdf(power)

    p_bar = (p_control + r * p_treatment) / (1.0 + r)
    term_null = z_alpha * math.sqrt(p_bar * (1.0 - p_bar) * (1.0 + 1.0 / r))
    term_alt = z_beta * math.sqrt(p_control * (1.0 - p_control) + (p_treatment * (1.0 - p_treatment)) / r)
    n_c_raw = ((term_null + term_alt) ** 2) / (diff ** 2)

    if continuity_correction:
        n_c_raw = (n_c_raw / 4.0) * (
            (1.0 + math.sqrt(1.0 + (2.0 * (r + 1.0)) / (r * n_c_raw * diff))) ** 2
        )

    n_control = int(math.ceil(n_c_raw))
    n_treatment = int(math.ceil(n_control * r))
    total_n = n_control + n_treatment
    waves_needed = int(math.ceil(total_n / max(1, eligible_per_wave)))

    return {
        "allocation_ratio": r,
        "n_control": n_control,
        "n_treatment": n_treatment,
        "total_n": total_n,
        "n_control_raw": round(n_c_raw, 2),
        "eligible_per_wave": eligible_per_wave,
        "waves_needed": waves_needed,
        "alpha_two_sided": alpha,
        "target_power": power,
        "continuity_correction": continuity_correction,
    }


def binomial_pmf(n: int, k: int, p: float) -> float:
    if k < 0 or k > n:
        return 0.0
    if p <= 0.0:
        return 1.0 if k == 0 else 0.0
    if p >= 1.0:
        return 1.0 if k == n else 0.0
    return math.comb(n, k) * (p ** k) * ((1.0 - p) ** (n - k))


def compute_cap_binding_risk(
    treatment_count: int,
    offer_rupees: int,
    max_budget: int,
    assumed_redemption_rate: float,
    warn_threshold: float = 0.10,
) -> Dict[str, Any]:
    """
    Computes probability that customer redemptions exceed the merchant's rupee cap
    when passes are issued to ALL nudged customers (Decision 1).
    Suggests the smallest multiple of offer_rupees keeping overrun risk <= warn_threshold.
    """
    n = max(0, int(treatment_count))
    offer = max(1, int(offer_rupees))
    cap = max(0, int(max_budget))
    p = min(1.0, max(0.0, float(assumed_redemption_rate)))

    face_exposure_inr = n * offer
    max_funded_redemptions = cap // offer

    prob_exceeds_cap = sum(binomial_pmf(n, k, p) for k in range(max_funded_redemptions + 1, n + 1))
    prob_hits_or_exceeds = sum(binomial_pmf(n, k, p) for k in range(max(1, max_funded_redemptions), n + 1))

    suggested_redemptions = max_funded_redemptions
    for q in range(max_funded_redemptions, n + 1):
        tail_q = sum(binomial_pmf(n, k, p) for k in range(q + 1, n + 1))
        if tail_q <= warn_threshold + 1e-12:
            suggested_redemptions = q
            break

    suggested_cap_inr = suggested_redemptions * offer
    warn = prob_exceeds_cap > warn_threshold

    return {
        "passes_issued": n,
        "offer_rupees": offer,
        "face_exposure_inr": face_exposure_inr,
        "max_budget_inr": cap,
        "max_funded_redemptions": max_funded_redemptions,
        "assumed_redemption_rate": round(p, 4),
        "prob_exceeds_cap": round(prob_exceeds_cap, 4),
        "prob_exceeds_cap_pct": round(prob_exceeds_cap * 100.0, 1),
        "prob_hits_or_exceeds_cap": round(prob_hits_or_exceeds, 4),
        "prob_hits_or_exceeds_cap_pct": round(prob_hits_or_exceeds * 100.0, 1),
        "warn_threshold_pct": round(warn_threshold * 100.0, 1),
        "warn_above_threshold": warn,
        "suggested_max_redemptions": suggested_redemptions,
        "suggested_cap_inr": suggested_cap_inr,
    }


def evaluate_itt_holdout_and_profit(
    treatment_count: int,
    itt_treatment_returned: int,
    holdout_count: int,
    holdout_returned: int,
    funded_redemptions: int,
    refused_redemptions: int,
    cap_reached: bool,
    offer_rupees: int,
    max_budget: int,
    gross_returning_sales_inr: float,
    funded_redeemed_sales_inr: float,
    gross_margin_pct: float = 30.0,
    paytm_fee_pct: float = 5.0,
    alpha: float = 0.05,
    target_power: float = 0.80,
) -> Dict[str, Any]:
    """
    Evaluates causal lift strictly as Intention-to-Treat (ITT: itt_treatment_returned / treatment_count
    vs holdout_returned / holdout_count) so holdout inference is unchanged when the spending cap binds,
    while computing merchant profit ROI from actual funded spend and all redeemed bills.
    """
    n_t = max(1, int(treatment_count))
    n_c = max(1, int(holdout_count))
    k_t = int(itt_treatment_returned)
    k_c = int(holdout_returned)

    t_rate_pct = round((k_t / n_t) * 100.0, 2)
    c_rate_pct = round((k_c / n_c) * 100.0, 2)
    abs_lift_pp = round(t_rate_pct - c_rate_pct, 2)

    ci_t = wilson_ci_95(k_t, n_t, alpha=alpha)
    ci_c = wilson_ci_95(k_c, n_c, alpha=alpha)
    fisher = fisher_exact_2x2(k_t, n_t - k_t, k_c, n_c - k_c)

    p_c_for_pow = min(0.95, max(0.02, k_c / n_c if k_c > 0 else 0.125))
    p_t_for_pow = min(0.98, max(p_c_for_pow + 0.05, k_t / n_t if k_t > 0 else 0.375))
    alloc_ratio = round(n_t / n_c, 4)

    power_80_20 = required_sample_size_two_prop(
        p_c_for_pow, p_t_for_pow, alpha=alpha, power=target_power, allocation_ratio=alloc_ratio, eligible_per_wave=n_t + n_c
    )
    power_even = required_sample_size_two_prop(
        p_c_for_pow, p_t_for_pow, alpha=alpha, power=target_power, allocation_ratio=1.0, eligible_per_wave=n_t + n_c
    )

    is_underpowered = (n_t + n_c) < power_80_20["total_n"]
    is_significant = (not is_underpowered) and (fisher["p_two_sided"] < alpha)

    # Incremental sales & profit accounting
    organic_expected_visits = (k_c / n_c) * n_t
    net_incremental_visits = max(0.0, k_t - organic_expected_visits)
    avg_returning_bill = (gross_returning_sales_inr / k_t) if k_t > 0 else 0.0
    incremental_sales_inr = round(net_incremental_visits * avg_returning_bill, 2)

    budget_spent_inr = funded_redemptions * offer_rupees
    organic_subsidy_inr = round(min(float(budget_spent_inr), organic_expected_visits * offer_rupees), 2)

    gross_sales_multiple = round(incremental_sales_inr / max(1.0, float(budget_spent_inr)), 2) if budget_spent_inr > 0 else 0.0
    incremental_gross_profit_inr = round(incremental_sales_inr * (gross_margin_pct / 100.0), 2)
    gross_profit_multiple = round(incremental_gross_profit_inr / max(1.0, float(budget_spent_inr)), 2) if budget_spent_inr > 0 else 0.0

    net_profit_pre_fee_inr = round(incremental_gross_profit_inr - budget_spent_inr, 2)
    net_roi_pre_fee_pct = round((net_profit_pre_fee_inr / max(1.0, float(budget_spent_inr))) * 100.0, 1) if budget_spent_inr > 0 else 0.0

    # Decision 4: Paytm 5% fee applies to all funded redeemed bills (including organic returners)
    paytm_fee_inr = round(funded_redeemed_sales_inr * (paytm_fee_pct / 100.0), 2)
    net_profit_post_fee_inr = round(net_profit_pre_fee_inr - paytm_fee_inr, 2)
    net_roi_post_fee_pct = round((net_profit_post_fee_inr / max(1.0, float(budget_spent_inr))) * 100.0, 1) if budget_spent_inr > 0 else 0.0

    breakeven_pre_fee_pct = round((budget_spent_inr / incremental_sales_inr) * 100.0, 1) if incremental_sales_inr > 0 else 100.0
    breakeven_post_fee_pct = round(((budget_spent_inr + paytm_fee_inr) / incremental_sales_inr) * 100.0, 1) if incremental_sales_inr > 0 else 100.0

    return {
        "itt": {
            "treatment_count": n_t,
            "treatment_returned": k_t,
            "treatment_rate_pct": t_rate_pct,
            "treatment_wilson_95_ci": list(ci_t),
            "holdout_count": n_c,
            "holdout_returned": k_c,
            "holdout_rate_pct": c_rate_pct,
            "holdout_wilson_95_ci": list(ci_c),
            "absolute_lift_pp": abs_lift_pp,
            "fisher_p_two_sided": fisher["p_two_sided"],
            "fisher_p_one_sided_greater": fisher["p_one_sided_greater"],
            "is_underpowered": is_underpowered,
            "is_statistically_significant": is_significant,
            "status_banner": (
                "Confirmed statistically significant lift"
                if is_significant
                else f"Directional simulation (interim: p = {fisher['p_two_sided']:.2f}; needs ~{power_80_20['total_n']} total across ~{power_80_20['waves_needed']} waves at 80/20)"
            ),
        },
        "power": {
            "at_campaign_split_80_20": power_80_20,
            "at_even_split_50_50": power_even,
        },
        "cap_accounting": {
            "passes_issued": n_t,
            "face_exposure_inr": n_t * offer_rupees,
            "max_budget_inr": max_budget,
            "max_funded_redemptions": max_budget // max(1, offer_rupees),
            "funded_redemptions": funded_redemptions,
            "refused_redemptions": refused_redemptions,
            "cap_reached": bool(cap_reached),
            "budget_spent_inr": budget_spent_inr,
        },
        "profit_waterfall": {
            "gross_returning_sales_inr": round(gross_returning_sales_inr, 2),
            "funded_redeemed_sales_inr": round(funded_redeemed_sales_inr, 2),
            "organic_expected_visits": round(organic_expected_visits, 2),
            "organic_subsidy_inr": organic_subsidy_inr,
            "net_incremental_visits": round(net_incremental_visits, 2),
            "incremental_sales_inr": incremental_sales_inr,
            "gross_sales_multiple": gross_sales_multiple,
            "assumed_gross_margin_pct": gross_margin_pct,
            "incremental_gross_profit_inr": incremental_gross_profit_inr,
            "gross_profit_multiple": gross_profit_multiple,
            "net_profit_pre_fee_inr": net_profit_pre_fee_inr,
            "net_roi_pre_fee_pct": net_roi_pre_fee_pct,
            "paytm_fee_pct": paytm_fee_pct,
            "paytm_fee_on_all_redeemed_bills_inr": paytm_fee_inr,
            "net_profit_post_fee_inr": net_profit_post_fee_inr,
            "net_roi_post_fee_pct": net_roi_post_fee_pct,
            "breakeven_margin_pre_fee_pct": breakeven_pre_fee_pct,
            "breakeven_margin_post_fee_pct": breakeven_post_fee_pct,
        },
    }


def simulate_dose_response_curve(
    offers_inr: List[int] = [0, 10, 15, 20, 25, 30, 40],
    treatment_count: int = 32,
    holdout_count: int = 8,
    max_budget: int = 300,
    avg_bill_inr: float = 217.50,
    gross_margin_pct: float = 30.0,
    paytm_fee_pct: float = 5.0,
    seed: int = 20261025,
) -> List[Dict[str, Any]]:
    """
    Randomized saturating dose-response simulation (SIMULATED, Evidence Grade B/C).
    Draws customer return visits independently of max_budget first, then applies the spend cap stop.
    """
    p_base = 0.125
    p_ceiling = 0.50
    scale = 22.0
    rows: List[Dict[str, Any]] = []

    for idx, offer in enumerate(offers_inr):
        rng = random.Random(seed + idx * 977)
        p_offer = p_base if offer <= 0 else p_base + (p_ceiling - p_base) * (1.0 - math.exp(-offer / scale))

        treat_draws = [1 if rng.random() < p_offer else 0 for _ in range(treatment_count)]
        ctrl_draws = [1 if rng.random() < p_base else 0 for _ in range(holdout_count)]

        itt_ret = sum(treat_draws)
        ctrl_ret = sum(ctrl_draws)

        if offer <= 0:
            funded = 0
            refused = 0
            cap_hit = False
        else:
            max_red = max_budget // offer
            funded = min(itt_ret, max_red)
            refused = max(0, itt_ret - funded)
            cap_hit = (funded * offer) >= max_budget and max_budget > 0

        ev = evaluate_itt_holdout_and_profit(
            treatment_count=treatment_count,
            itt_treatment_returned=itt_ret,
            holdout_count=holdout_count,
            holdout_returned=ctrl_ret,
            funded_redemptions=funded,
            refused_redemptions=refused,
            cap_reached=cap_hit,
            offer_rupees=max(1, offer) if offer > 0 else 0,
            max_budget=max_budget,
            gross_returning_sales_inr=itt_ret * avg_bill_inr,
            funded_redeemed_sales_inr=funded * avg_bill_inr,
            gross_margin_pct=gross_margin_pct,
            paytm_fee_pct=paytm_fee_pct,
        )
        rows.append(
            {
                "offer_rupees": offer,
                "true_response_prob": round(p_offer, 4),
                "itt_treatment_returned": itt_ret,
                "holdout_returned": ctrl_ret,
                "funded_redemptions": funded,
                "refused_redemptions": refused,
                "cap_reached": cap_hit,
                "budget_spent_inr": funded * offer,
                "net_profit_pre_fee_inr": ev["profit_waterfall"]["net_profit_pre_fee_inr"] if offer > 0 else 0.0,
                "net_profit_post_fee_inr": ev["profit_waterfall"]["net_profit_post_fee_inr"] if offer > 0 else 0.0,
            }
        )
    return rows
