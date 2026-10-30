import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_YAML_PATH = REPO_ROOT / "config" / "default.yaml"
SARVAM_YAML_PATH = REPO_ROOT / "config" / "sarvam.yaml"
DOTENV_PATH = REPO_ROOT / ".env"


def _parse_bool(val: Optional[str], default: bool = False) -> bool:
    if val is None or val.strip() == "":
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


def _load_dotenv_non_destructive(dotenv_path: Path) -> None:
    """Load local .env key-values into os.environ only if not already set."""
    if not dotenv_path.exists():
        return
    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = val


def _load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


@dataclass(frozen=True)
class Settings:
    app_name: str
    app_version: str
    live_demo_url: str
    public_deploy: bool
    admin_token: str

    # Session isolation & resource bounds
    isolate_visitors: bool
    session_cookie_name: str
    session_header_name: str
    session_ttl_seconds: int
    max_active_sessions: int
    max_session_db_bytes: int
    max_total_sessions_bytes: int
    session_storage_dir: Path

    # Economics & guardrails
    default_gross_margin_pct: float
    paytm_promo_fee_pct: float
    steady_state_campaigns_per_month: float
    steady_state_redeemed_gmv_monthly_inr: float
    max_discount_floor_pct: float
    cooldown_days: int

    # Statistical power & cap-binding alert
    default_allocation_ratio: float
    alpha_two_sided: float
    target_power: float
    cap_overrun_warn_threshold: float
    assumed_redemption_rates: Dict[str, float] = field(default_factory=dict)

    # Keyless Sarvam AI settings
    sarvam_enabled: bool = False
    sarvam_live_calls_enabled: bool = False
    sarvam_api_key: str = ""
    sarvam_base_url: str = "https://api.sarvam.ai"
    sarvam_timeout_seconds: float = 8.0
    sarvam_tts_endpoint: str = "/text-to-speech"
    sarvam_tts_model: str = "bulbul:v3"
    sarvam_tts_cost_per_10k_inr: float = 30.0
    sarvam_speakers: Dict[str, str] = field(default_factory=dict)
    sarvam_stt_endpoint: str = "/speech-to-text"
    sarvam_stt_model: str = "saaras:v3"
    sarvam_stt_cost_per_hour_inr: float = 30.0
    sarvam_translate_endpoint: str = "/translate"
    sarvam_translate_cost_per_10k_inr: float = 20.0
    sarvam_tts_cap_pct: float = 15.0
    sarvam_stt_cap_pct: float = 15.0
    sarvam_total_cap_pct: float = 30.0
    sarvam_ledger_path: Path = REPO_ROOT / "data" / "sarvam_credit_ledger.json"
    sarvam_cache_dir: Path = REPO_ROOT / "data" / "audio_cache"

    # Optional Groq free-tier English Q&A
    groq_enabled: bool = False
    groq_api_key: str = ""
    groq_base_url: str = "https://api.groq.com/openai/v1"

    @property
    def sarvam_live_allowed(self) -> bool:
        """Live Sarvam calls are strictly forbidden on public deployments."""
        if self.public_deploy:
            return False
        return bool(
            self.sarvam_enabled
            and self.sarvam_live_calls_enabled
            and len(self.sarvam_api_key.strip()) > 0
        )

    @property
    def groq_live_allowed(self) -> bool:
        """Live Groq calls are strictly forbidden on public deployments."""
        if self.public_deploy:
            return False
        return bool(self.groq_enabled and len(self.groq_api_key.strip()) > 0)


_CACHED_SETTINGS: Optional[Settings] = None


def load_settings(force_reload: bool = False) -> Settings:
    global _CACHED_SETTINGS
    if _CACHED_SETTINGS is not None and not force_reload:
        return _CACHED_SETTINGS

    _load_dotenv_non_destructive(DOTENV_PATH)
    d_cfg = _load_yaml(DEFAULT_YAML_PATH)
    s_cfg = _load_yaml(SARVAM_YAML_PATH)

    app_sec = d_cfg.get("app", {})
    sess_sec = d_cfg.get("sessions", {})
    econ_sec = d_cfg.get("economics", {})
    exp_sec = d_cfg.get("experiment", {})

    tts_sec = s_cfg.get("tts", {})
    stt_sec = s_cfg.get("stt", {})
    tr_sec = s_cfg.get("translate", {})
    cap_sec = s_cfg.get("credit_caps", {})

    # Render automatically sets RENDER=true; default public_deploy=True on Render unless overridden
    render_detected = _parse_bool(os.environ.get("RENDER"), False)
    default_pub = bool(app_sec.get("public_deploy_default", False)) or render_detected
    public_deploy = _parse_bool(os.environ.get("PUBLIC_DEPLOY"), default_pub)

    isolate_default = bool(sess_sec.get("isolate_visitors", True))
    isolate_visitors = _parse_bool(os.environ.get("ISOLATE_VISITORS"), isolate_default)

    ledger_rel = cap_sec.get("ledger_path", "data/sarvam_credit_ledger.json")
    cache_rel = cap_sec.get("cache_dir", "data/audio_cache")
    sess_rel = sess_sec.get("storage_dir", "app/sessions_db")

    ledger_path = Path(os.environ.get("SARVAM_LEDGER_PATH", str(REPO_ROOT / ledger_rel)))
    cache_dir = Path(os.environ.get("SARVAM_CACHE_DIR", str(REPO_ROOT / cache_rel)))
    sess_dir = Path(os.environ.get("SESSION_STORAGE_DIR", str(REPO_ROOT / sess_rel)))

    _CACHED_SETTINGS = Settings(
        app_name=str(app_sec.get("name", "PaytmAI VyaparVoice")),
        app_version=str(app_sec.get("version", "1.1.0")),
        live_demo_url=str(app_sec.get("live_demo_url", "https://paytmai-vyaparvoice.onrender.com")),
        public_deploy=public_deploy,
        admin_token=os.environ.get("ADMIN_TOKEN", "").strip(),
        isolate_visitors=isolate_visitors,
        session_cookie_name=str(sess_sec.get("cookie_name", "vyaparvoice_sid")),
        session_header_name=str(sess_sec.get("header_name", "X-Demo-Session")),
        session_ttl_seconds=int(os.environ.get("SESSION_TTL_SECONDS", sess_sec.get("ttl_seconds", 1800))),
        max_active_sessions=int(os.environ.get("MAX_ACTIVE_SESSIONS", sess_sec.get("max_active_sessions", 64))),
        max_session_db_bytes=int(os.environ.get("MAX_SESSION_DB_BYTES", sess_sec.get("max_session_db_bytes", 2097152))),
        max_total_sessions_bytes=int(
            os.environ.get("MAX_TOTAL_SESSIONS_BYTES", sess_sec.get("max_total_sessions_bytes", 33554432))
        ),
        session_storage_dir=sess_dir,
        default_gross_margin_pct=float(econ_sec.get("default_gross_margin_pct", 30.0)),
        paytm_promo_fee_pct=float(econ_sec.get("paytm_promo_fee_pct", 5.0)),
        steady_state_campaigns_per_month=float(econ_sec.get("steady_state_campaigns_per_month", 0.782)),
        steady_state_redeemed_gmv_monthly_inr=float(econ_sec.get("steady_state_redeemed_gmv_monthly_inr", 2040.0)),
        max_discount_floor_pct=float(econ_sec.get("max_discount_floor_pct", 22.0)),
        cooldown_days=int(econ_sec.get("cooldown_days", 14)),
        default_allocation_ratio=float(exp_sec.get("default_allocation_ratio", 4.0)),
        alpha_two_sided=float(exp_sec.get("alpha_two_sided", 0.05)),
        target_power=float(exp_sec.get("target_power", 0.80)),
        cap_overrun_warn_threshold=float(exp_sec.get("cap_overrun_warn_threshold", 0.10)),
        assumed_redemption_rates=dict(
            exp_sec.get("assumed_redemption_rates", {"CMP-WINBACK-01": 0.375, "CMP-DEADHOUR-02": 0.407, "default": 0.35})
        ),
        sarvam_enabled=_parse_bool(os.environ.get("SARVAM_ENABLED"), False),
        sarvam_live_calls_enabled=_parse_bool(os.environ.get("SARVAM_LIVE_CALLS_ENABLED"), False),
        sarvam_api_key=os.environ.get("SARVAM_API_KEY", "").strip(),
        sarvam_base_url=os.environ.get("SARVAM_BASE_URL", str(s_cfg.get("base_url", "https://api.sarvam.ai"))).rstrip("/"),
        sarvam_timeout_seconds=float(s_cfg.get("timeout_seconds", 8.0)),
        sarvam_tts_endpoint=str(tts_sec.get("endpoint", "/text-to-speech")),
        sarvam_tts_model=str(tts_sec.get("model", "bulbul:v3")),
        sarvam_tts_cost_per_10k_inr=float(tts_sec.get("cost_per_10k_chars_inr", 30.0)),
        sarvam_speakers=dict(tts_sec.get("speakers", {"en-IN": "anushka", "kn-IN": "anushka", "hi-IN": "abhilash"})),
        sarvam_stt_endpoint=str(stt_sec.get("endpoint", "/speech-to-text")),
        sarvam_stt_model=str(stt_sec.get("model", "saaras:v3")),
        sarvam_stt_cost_per_hour_inr=float(stt_sec.get("cost_per_hour_inr", 30.0)),
        sarvam_translate_endpoint=str(tr_sec.get("endpoint", "/translate")),
        sarvam_translate_cost_per_10k_inr=float(tr_sec.get("cost_per_10k_chars_inr", 20.0)),
        sarvam_tts_cap_pct=float(cap_sec.get("tts_max_share_pct", 15.0)),
        sarvam_stt_cap_pct=float(cap_sec.get("stt_max_share_pct", 15.0)),
        sarvam_total_cap_pct=float(cap_sec.get("total_max_share_pct", 30.0)),
        sarvam_ledger_path=ledger_path,
        sarvam_cache_dir=cache_dir,
        groq_enabled=_parse_bool(os.environ.get("GROQ_ENABLED"), False),
        groq_api_key=os.environ.get("GROQ_API_KEY", "").strip(),
        groq_base_url=os.environ.get("GROQ_BASE_URL", "https://api.groq.com/openai/v1").rstrip("/"),
    )
    return _CACHED_SETTINGS


def get_settings() -> Settings:
    return load_settings(force_reload=False)
