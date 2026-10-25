import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .database import init_and_seed_db
from .engine import (
    get_dashboard_overview,
    get_voice_briefing,
    approve_campaign,
    simulate_campaign_48h,
    execute_ops_action,
    handle_voice_command,
)

app = FastAPI(
    title="PaytmAI VyaparVoice — Merchant Growth Autopilot",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.on_event("startup")
def on_startup() -> None:
    init_and_seed_db(force_reset=False)


class ApprovePayload(BaseModel):
    via: str = "1-Tap Soundbox"


class VoicePayload(BaseModel):
    utterance: str
    lang: str = "en"


@app.get("/")
def serve_index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "PaytmAI VyaparVoice"}


@app.get("/api/overview")
def api_overview():
    return get_dashboard_overview()


@app.get("/api/briefing")
def api_briefing(lang: str = "en"):
    return get_voice_briefing(lang)


@app.post("/api/campaigns/{campaign_id}/approve")
def api_approve_campaign(campaign_id: str, payload: ApprovePayload):
    try:
        cmp_data = approve_campaign(campaign_id, via=payload.via)
        return {"ok": True, "campaign": cmp_data}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/api/campaigns/{campaign_id}/simulate")
def api_simulate_campaign(campaign_id: str):
    try:
        cmp_data = simulate_campaign_48h(campaign_id)
        return {"ok": True, "campaign": cmp_data}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/api/ops/{action_id}/execute")
def api_execute_ops(action_id: str):
    try:
        ops_data = execute_ops_action(action_id)
        return {"ok": True, "ops_action": ops_data}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/api/voice-command")
def api_voice_command(payload: VoicePayload):
    return handle_voice_command(payload.utterance, payload.lang)


@app.post("/api/reset")
def api_reset():
    init_and_seed_db(force_reset=True)
    return {"ok": True, "message": "Demo database reset to fresh 8:30 PM evening state."}
