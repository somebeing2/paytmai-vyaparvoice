from contextlib import asynccontextmanager
import os
import threading
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .config import get_settings
from .copy_lint import assert_valid_merchant_copy
from .database import DB_PATH, get_conn, init_and_seed_db, use_db_path
from .engine import (
    answer_merchant_question,
    approve_campaign,
    evaluate_guardrail_attack,
    evaluate_what_if,
    execute_ops_action,
    explain_campaign_simply,
    get_dashboard_overview,
    get_voice_briefing,
    handle_voice_command,
    resolve_pending_cap_change,
    set_campaign_stop_loss,
    simulate_campaign_48h,
    simulate_campaign_spend,
    step_live_campaign_scans,
    update_campaign_cap,
)
from .providers.groq_qa import get_groq_qa
from .providers.sarvam import SarvamProvider
from .security import verify_admin_token
from .sessions import SessionIsolationMiddleware, active_session_summary
from .stats import (
    compute_breakeven_lift,
    compute_pooled_pilot_power_table,
    required_sample_size_two_prop,
)
from .templates import render_why_explanation


def _warm_baseline_db_async() -> None:
    try:
        with use_db_path(DB_PATH):
            init_and_seed_db(force_reset=False)
    except Exception:
        pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Defer SQLite seed onto a daemon thread so Uvicorn binds 0.0.0.0:$PORT immediately on 0.1-CPU Render Free tier.
    threading.Thread(target=_warm_baseline_db_async, daemon=True).start()
    yield


app = FastAPI(
    title="PaytmAI VyaparVoice - Merchant Growth Autopilot",
    version="1.3.1",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SessionIsolationMiddleware)

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class ApprovePayload(BaseModel):
    via: str = "1-Tap Soundbox"
    custom_max_budget: Optional[int] = None


class SimulatePayload(BaseModel):
    mode: str = "canonical"
    seed: int = 20261025
    override_max_budget: Optional[int] = None


class VoicePayload(BaseModel):
    utterance: str
    lang: str = "en"


class CapUpdatePayload(BaseModel):
    new_cap_inr: int
    actor: str = "dashboard"
    confirmed: bool = True
    period_key: str = "48_hours"
    lang: str = "en"
    source: Optional[str] = None


class CapConfirmPayload(BaseModel):
    confirm: bool = True
    actor: str = "voice"
    source: Optional[str] = None


class STTRequestPayload(BaseModel):
    audio_base64: Optional[str] = None
    fallback_utterance: str = ""
    lang: str = "en"


class StepLivePayload(BaseModel):
    step_size: int = 4


class SimulateSpendPayload(BaseModel):
    target_pct: Optional[int] = None
    add_rupees: Optional[int] = None
    post_cap_regular_customers: Optional[int] = None


class StopLossPayload(BaseModel):
    pause: bool = True
    actor: str = "Merchant Stop-Loss"


class GuardrailAttackPayload(BaseModel):
    attack_text: str
    record_audit: bool = True


class WhatIfPayload(BaseModel):
    offer_rupees: int = 25
    min_bill: int = 150
    max_budget: int = 300
    gross_margin_pct: float = 30.0
    paytm_fee_pct: float = 5.0
    allocation_ratio: float = 4.0


class MerchantQAPayload(BaseModel):
    question: str
    lang: str = "en"


class TTSRequestPayload(BaseModel):
    text: str
    lang: str = "en"


@app.api_route("/", methods=["GET", "HEAD"])
def serve_index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.api_route("/replay", methods=["GET", "HEAD"])
def serve_offline_replay():
    return FileResponse(os.path.join(STATIC_DIR, "demo_replay.html"))


@app.api_route("/health", methods=["GET", "HEAD"])
@app.api_route("/api/health", methods=["GET", "HEAD"])
def health(request: Request):
    settings = get_settings()
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version,
        "public_deploy": settings.public_deploy,
        "paid_calls_blocked": settings.public_deploy or not settings.sarvam_live_allowed,
        "groq_live_blocked": settings.public_deploy or not settings.groq_live_allowed,
        "session_id": getattr(request.state, "demo_session_id", None),
        "sessions": active_session_summary(),
    }


@app.get("/api/overview")
def api_overview():
    return get_dashboard_overview()


@app.get("/api/briefing")
def api_briefing(lang: str = "en", detail: bool = False):
    return get_voice_briefing(lang, detail=detail)


@app.post("/api/tts")
def api_tts(payload: TTSRequestPayload):
    txt = (payload.text or "").strip()
    if not txt:
        raise HTTPException(status_code=400, detail="Text is required for TTS.")
    lang_norm = (payload.lang or "en").strip().lower()
    lang_code = "hi-IN" if lang_norm.startswith("hi") else ("kn-IN" if lang_norm.startswith("kn") else "en-IN")
    provider = SarvamProvider()
    res = provider.synthesize(txt[:1200], lang_code=lang_code, strict=False)
    return {
        "ok": True,
        "lang_code": res.lang_code,
        "provider": res.provider,
        "mode": res.mode,
        "cached": res.cached,
        "audio_base64": res.audio_base64,
        "mime_type": res.mime_type,
        "fallback_reason": res.fallback_reason,
    }


@app.get("/api/power")
def api_power(
    p_control: float = 0.125,
    p_treatment: float = 0.375,
    allocation_ratio: float = 4.0,
    alpha: float = 0.05,
    power: float = 0.80,
):
    try:
        res = required_sample_size_two_prop(
            p_control=p_control,
            p_treatment=p_treatment,
            alpha=alpha,
            power=power,
            allocation_ratio=allocation_ratio,
        )
        res["pooled_50_shop_pilot"] = compute_pooled_pilot_power_table(p_control=p_control, alpha=alpha)
        res["breakeven_lift"] = compute_breakeven_lift(p_control=p_control)
        return res
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/api/breakeven")
def api_breakeven(
    p_control: float = 0.125,
    avg_bill_inr: float = 217.50,
    gross_margin_pct: float = 30.0,
    offer_rupees: float = 25.0,
    paytm_fee_pct: float = 5.0,
):
    if not (0.01 <= p_control <= 0.90) or avg_bill_inr <= 0 or gross_margin_pct <= 0 or offer_rupees < 0:
        raise HTTPException(status_code=400, detail="Invalid break-even calculator parameters.")
    gp_visit = round(avg_bill_inr * (gross_margin_pct / 100.0), 2)
    fee_visit = round(avg_bill_inr * (paytm_fee_pct / 100.0), 2)
    if gp_visit <= offer_rupees:
        raise HTTPException(
            status_code=400,
            detail=f"Offer Rs {offer_rupees:.0f} exceeds gross profit per visit Rs {gp_visit:.2f}; campaign cannot break even.",
        )
    res = compute_breakeven_lift(
        p_control=p_control,
        avg_bill_inr=avg_bill_inr,
        gross_margin_pct=gross_margin_pct,
        offer_rupees=offer_rupees,
        paytm_fee_pct=paytm_fee_pct,
    )
    res["gross_profit_per_visit_inr"] = gp_visit
    res["paytm_fee_per_redeemed_visit_inr"] = fee_visit
    plain = (
        f"At {gross_margin_pct:.0f} percent shop margin on a {avg_bill_inr:.0f} rupee average bill, "
        f"each extra visit brings {gp_visit:.0f} rupees before cashback. "
        f"To cover a {offer_rupees:.0f} rupee pass, return visits must rise from {res['baseline_pct']:.1f} percent "
        f"to at least {res['breakeven_rate_pre_fee_pct']:.1f} percent before fee ({res['breakeven_rate_post_fee_pct']:.1f} percent after fee)."
    )
    res["merchant_summary"] = assert_valid_merchant_copy(plain)
    return res


@app.post("/api/guardrail-check")
def api_guardrail_check(payload: GuardrailAttackPayload):
    return evaluate_guardrail_attack(payload.attack_text, record_audit=payload.record_audit)


@app.post("/api/what-if")
def api_what_if(payload: WhatIfPayload):
    return evaluate_what_if(
        offer_rupees=payload.offer_rupees,
        min_bill=payload.min_bill,
        max_budget=payload.max_budget,
        gross_margin_pct=payload.gross_margin_pct,
        paytm_fee_pct=payload.paytm_fee_pct,
        allocation_ratio=payload.allocation_ratio,
    )


@app.get("/api/why/{item_id}")
def api_why(item_id: str):
    if item_id == "KPI-PROFIT":
        ov = get_dashboard_overview()
        k = ov["kpis"]
        state = k["profit_state"]
        pre = k["estimated_net_profit_pre_fee_inr"]
        post = k["estimated_net_profit_post_fee_inr"]
        if state == "NO_OFFER_RUN_YET":
            plain = assert_valid_merchant_copy(
                "No offer has run yet, so cashback spent is Rs 0 and estimated profit after offer is Rs 0. "
                "Once customers visit, we multiply extra sales by your 30 percent assumed shop margin and subtract cashback spent. "
                "Marked Estimate (Grade C) because UPI bills show payment totals, while shop margin is an assumption."
            )
        elif state == "BREAK_EVEN":
            plain = assert_valid_merchant_copy(
                "Your offer is right at zero net gain before fee: extra shop margin exactly matches cashback spent. "
                "Marked Estimate (Grade C) because your 30 percent shop margin is an assumed percentage."
            )
        else:
            plain = assert_valid_merchant_copy(
                f"Estimated profit after offer is Rs {pre:.0f} before fee (Rs {post:.2f} after 5 percent Paytm fee). "
                "Formula: extra sales multiplied by 30 percent assumed shop margin minus cashback spent. "
                "Marked Estimate (Grade C) because shop margin and fee are explicit assumptions, not observed on QR receipts."
            )
        return {
            "item_id": "KPI-PROFIT",
            "evidence_grade": "C",
            "profit_state": state,
            "merchant_plain": plain,
            "technical_provenance": k["profit_formula"],
        }
    conn = get_conn()
    cur = conn.cursor()
    row = cur.execute("SELECT * FROM campaigns WHERE campaign_id = ?", (item_id,)).fetchone()
    if row:
        conn.close()
        return render_why_explanation(item_id, dict(row))
    op_row = cur.execute("SELECT * FROM ops_actions WHERE action_id = ?", (item_id,)).fetchone()
    conn.close()
    if op_row:
        return render_why_explanation(item_id, dict(op_row))
    raise HTTPException(status_code=404, detail=f"Unknown recommendation id: {item_id}")


@app.post("/api/campaigns/{campaign_id}/approve")
def api_approve_campaign(campaign_id: str, payload: Optional[ApprovePayload] = None):
    body = payload or ApprovePayload()
    try:
        cmp_data = approve_campaign(
            campaign_id,
            via=body.via,
            custom_max_budget=body.custom_max_budget,
        )
        return {"ok": True, "campaign": cmp_data}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@app.post("/api/campaigns/{campaign_id}/cap")
def api_update_campaign_cap(campaign_id: str, payload: CapUpdatePayload):
    try:
        cmp_data = update_campaign_cap(
            campaign_id,
            new_cap_inr=payload.new_cap_inr,
            actor=payload.actor,
            confirmed=payload.confirmed,
            period_key=payload.period_key,
            lang=payload.lang,
            source=payload.source,
        )
        return {"ok": True, "campaign": cmp_data}
    except ValueError as exc:
        code = 404 if "not found" in str(exc).lower() else 400
        raise HTTPException(status_code=code, detail=str(exc))


@app.post("/api/campaigns/{campaign_id}/cap/confirm")
def api_confirm_campaign_cap(campaign_id: str, payload: Optional[CapConfirmPayload] = None):
    body = payload or CapConfirmPayload()
    try:
        cmp_data = resolve_pending_cap_change(
            campaign_id,
            confirm=body.confirm,
            actor=body.actor,
            source=body.source,
        )
        return {"ok": True, "campaign": cmp_data}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/campaigns/{campaign_id}/step-live")
def api_step_live_campaign(campaign_id: str, payload: Optional[StepLivePayload] = None):
    body = payload or StepLivePayload()
    try:
        cmp_data = step_live_campaign_scans(campaign_id, step_size=body.step_size)
        return {"ok": True, "campaign": cmp_data}
    except ValueError as exc:
        code = 404 if "not found" in str(exc).lower() else 400
        raise HTTPException(status_code=code, detail=str(exc))


@app.post("/api/campaigns/{campaign_id}/simulate-spend")
def api_simulate_campaign_spend(campaign_id: str, payload: Optional[SimulateSpendPayload] = None):
    body = payload or SimulateSpendPayload()
    try:
        cmp_data = simulate_campaign_spend(
            campaign_id,
            target_pct=body.target_pct,
            add_rupees=body.add_rupees,
            post_cap_regular_customers=body.post_cap_regular_customers,
        )
        return {
            "ok": True,
            "campaign": cmp_data,
            "newly_fired_alerts": cmp_data.get("newly_fired_alerts", []),
        }
    except ValueError as exc:
        code = 404 if "not found" in str(exc).lower() else 400
        raise HTTPException(status_code=code, detail=str(exc))


@app.post("/api/campaigns/{campaign_id}/stop-loss")
def api_stop_loss_campaign(campaign_id: str, payload: Optional[StopLossPayload] = None):
    body = payload or StopLossPayload()
    try:
        cmp_data = set_campaign_stop_loss(campaign_id, pause=body.pause, actor=body.actor)
        return {"ok": True, "campaign": cmp_data}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@app.post("/api/campaigns/{campaign_id}/simulate")
def api_simulate_campaign(campaign_id: str, payload: Optional[SimulatePayload] = None):
    body = payload or SimulatePayload()
    try:
        cmp_data = simulate_campaign_48h(
            campaign_id,
            mode=body.mode,
            seed=body.seed,
            override_max_budget=body.override_max_budget,
        )
        return {"ok": True, "campaign": cmp_data}
    except ValueError as exc:
        code = 404 if "not found" in str(exc).lower() else 400
        raise HTTPException(status_code=code, detail=str(exc))


@app.get("/api/campaigns/{campaign_id}/explain-simply")
def api_get_explain_simply(campaign_id: str, lang: str = "en"):
    try:
        return explain_campaign_simply(campaign_id, lang=lang)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@app.post("/api/ops/{action_id}/execute")
def api_execute_ops(action_id: str):
    try:
        ops_data = execute_ops_action(action_id)
        return {"ok": True, "ops_action": ops_data}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@app.post("/api/stt")
def api_stt(payload: STTRequestPayload):
    lang_norm = (payload.lang or "en").strip().lower()
    lang_code = "hi-IN" if lang_norm.startswith("hi") else ("kn-IN" if lang_norm.startswith("kn") else "en-IN")
    provider = SarvamProvider()
    res = provider.transcribe(
        audio_base64=payload.audio_base64 or "",
        lang_code=lang_code,
        strict=False,
    )
    return {
        "ok": True,
        "transcript": res.transcript or payload.fallback_utterance,
        "lang_code": res.lang_code,
        "provider": res.provider,
        "mode": res.mode,
        "fallback_reason": res.fallback_reason,
    }
@app.post("/api/voice-command")
def api_voice_command(payload: VoicePayload):
    return handle_voice_command(payload.utterance, payload.lang)


@app.post("/api/merchant-qa")
def api_merchant_qa(payload: MerchantQAPayload):
    try:
        return answer_merchant_question(payload.question, payload.lang)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/api/providers/groq-status")
def api_groq_status():
    return get_groq_qa().status_dict()


@app.post("/api/reset")
def api_reset(request: Request):
    init_and_seed_db(force_reset=True)
    return {
        "ok": True,
        "session_id": getattr(request.state, "demo_session_id", "local-default"),
        "message": "Your isolated demo session has been reset to the 8:30 PM closing state.",
    }


@app.post("/api/admin/reset-global")
def api_admin_reset_global(_authorized: bool = Depends(verify_admin_token)):
    with use_db_path(DB_PATH):
        init_and_seed_db(force_reset=True)
    return {"ok": True, "message": "Global baseline database reset."}


@app.get("/api/admin/provider-status")
def api_admin_provider_status(_authorized: bool = Depends(verify_admin_token)):
    provider = SarvamProvider()
    return {
        "ok": True,
        "sarvam": provider.status_dict(),
        "groq": get_groq_qa().status_dict(),
        "sessions": active_session_summary(),
    }
