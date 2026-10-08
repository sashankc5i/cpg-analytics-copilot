import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
(ROOT / "data").mkdir(exist_ok=True)


class Settings:
    groq_api_key = os.getenv("GROQ_API_KEY", "")
    groq_model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    groq_fast_model = os.getenv("GROQ_FAST_MODEL", "llama-3.1-8b-instant")
    state_db = os.getenv("STATE_DB", str(ROOT / "data" / "state.db"))
    analytics_url = os.getenv("ANALYTICS_DB_URL") or f"sqlite:///{ROOT / 'data' / 'cpg.db'}"
    jwt_secret = os.getenv("JWT_SECRET", "dev-secret-change-me")
    jwt_ttl_min = int(os.getenv("JWT_TTL_MIN", "480"))
    auth_mode = os.getenv("AUTH_MODE", "local")
    oidc_jwks_url = os.getenv("OIDC_JWKS_URL", "")
    oidc_audience = os.getenv("OIDC_AUDIENCE", "")
    oidc_issuer = os.getenv("OIDC_ISSUER", "")
    oidc_role_map = os.getenv("OIDC_ROLE_MAP", "")
    demo_password = os.getenv("DEMO_PASSWORD", "demo123")
    workflow_webhook = os.getenv("WORKFLOW_WEBHOOK_URL", "")
    bi_url = os.getenv("BI_DASHBOARD_URL", "https://app.powerbi.com/groups/me/reports/REPORT_ID")
    cors = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")]
    currency = os.getenv("CURRENCY_SYMBOL", "$")
    max_tool_rounds = int(os.getenv("MAX_TOOL_ROUNDS", "6"))
    radar_interval_min = int(os.getenv("RADAR_INTERVAL_MIN", "0"))
    auto_investigate_threshold = int(os.getenv("AUTO_INVESTIGATE_THRESHOLD", "60"))


settings = Settings()
