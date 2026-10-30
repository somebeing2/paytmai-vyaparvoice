from contextlib import asynccontextmanager
import os
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .config import get_settings
from .database import DB_PATH, init_and_seed_db, use_db_path
from .engine import (
    approve_campaign,
    execute_ops_action,
    get_dashboard_overview,
    get_voice_briefing,
    handle_voice_command,
    simulate_campaign_48h,
)
from .providers.sarvam import SarvamProvider
from .security import verify_admin_token
from .sessions import SessionIsolationMiddleware, active_session_summary
from .stats import (
    compute_breakeven_lift,
    compute_pooled_pilot_power_table,
    required_sample_size_two_prop,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    with use_db_path(DB_PATH):
        init_and_seed_db(force_reset=False)
    yield


app = FastAPI(
    title="PaytmAI VyaparVoice - Merchant Growth Autopilot",
    version="1.1.0",
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


@app.get("/")
def serve_index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/api/health")
def health(request: Request):
    settings = get_settings()
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version,
        "public_deploy": settings.public_deploy,
        "paid_calls_blocked": settings.public_deploy or not settings.sarvam_live_allowed,
        "session_id": getattr(request.state, "demo_session_id", None),
        "sessions": active_session_summary(),
    }


@app.get("/api/overview")
def api_overview():
    return get_dashboard_overview()


@app.get("/api/briefing")
def api_briefing(lang: str = "en"):
    return get_voice_briefing(lang)


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
        raise HTTPException(status_code=404, detail=str(exc))


@app.post("/api/ops/{action_id}/execute")
def api_execute_ops(action_id: str):
    try:
        ops_data = execute_ops_action(action_id)
        return {"ok": True, "ops_action": ops_data}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@app.post("/api/voice-command")
def api_voice_command(payload: VoicePayload):
    return handle_voice_command(payload.utterance, payload.lang)


@app.post("/api/reset")
def api_reset(request: Request):
    """Resets only the active visitor session database (never clobbers other visitors)."""
    init_and_seed_db(force_reset=True)
    return {
        "ok": True,
        "session_id": getattr(request.state, "demo_session_id", "local-default"),
        "message": "Your isolated demo session has been reset to the 8:30 PM closing state.",
    }


@app.post("/api/admin/reset-global")
def api_admin_reset_global(_authorized: bool = Depends(verify_admin_token)):
    """Protected global base-DB reset requiring X-Admin-Token header."""
    with use_db_path(DB_PATH):
        init_and_seed_db(force_reset=True)
    return {"ok": True, "message": "Global baseline database reset."}


@app.get("/api/admin/provider-status")
def api_admin_provider_status(_authorized: bool = Depends(verify_admin_token)):
    provider = SarvamProvider()
    return {"ok": True, "sarvam": provider.status_dict(), "sessions": active_session_summary()}
