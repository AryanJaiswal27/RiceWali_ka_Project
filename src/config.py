import os
from pathlib import Path
from pydantic import BaseModel, Field

# Base Directory Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
ERROR_CODES_PATH = DATA_DIR / "error_codes.json"
MANUALS_PATH = DATA_DIR / "industrial_manuals.md"
VECTOR_STORE_DIR = BASE_DIR / "vector_store_data"

# Auto-load .env file if present
ENV_PATH = BASE_DIR / ".env"
if ENV_PATH.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(dotenv_path=ENV_PATH)
    except ImportError:
        # Fallback basic parser for airgapped environments
        with open(ENV_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip().strip('"').strip("'")
                    if key not in os.environ:
                        os.environ[key] = val


def _resolve_ai_gateway_settings():
    """
    Dynamically configures either TCS GenAI Lab MaaS or Google Gemini API.
    If GEMINI_API_KEY is defined in environment or .env, switches gracefully to Gemini.
    Otherwise, preserves 100% default TCS GenAI Lab MaaS gateway parameters.
    """
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    maas_key = os.getenv("MAAS_API_KEY", "").strip()
    
    # Check if Gemini key is supplied either explicitly or via MAAS_API_KEY
    if gemini_key or (maas_key.startswith("AIzaSy") or maas_key.startswith("AQ.") or "gemini" in os.getenv("MODEL_NAME", "").lower()):
        active_key = gemini_key or maas_key
        base_url = os.getenv("MAAS_API_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai").rstrip("/")
        model = os.getenv("MODEL_NAME", "gemini-3.8-flash")
        embed_model = os.getenv("EMBEDDING_MODEL_NAME", "gemini-embedding-001")
        is_gemini = True
    else:
        active_key = maas_key
        base_url = os.getenv("MAAS_API_BASE_URL", "https://genailab.tcs.in/v1").rstrip("/")
        model = os.getenv("MODEL_NAME", "azure/genailab-maas-gpt-4o-mini")
        embed_model = os.getenv("EMBEDDING_MODEL_NAME", "azure/genailab-maas-text-embedding-3-large")
        is_gemini = False

    return active_key, base_url, model, embed_model, is_gemini


_active_key, _base_url, _model, _embed_model, _is_gemini = _resolve_ai_gateway_settings()


class SystemSettings(BaseModel):
    """
    Enterprise system configuration parameters.
    Supports TCS GenAI Lab MaaS by default, with seamless opt-in for Gemini API testing.
    """
    app_name: str = "AI Product Manual Troubleshooting Assistant"
    app_version: str = "1.0.0"
    
    # Gateway Provider Flag
    is_gemini_active: bool = Field(default_factory=lambda: _is_gemini)
    gemini_api_key: str = Field(default_factory=lambda: os.getenv("GEMINI_API_KEY", ""))

    # Model-as-a-Service (MaaS) OpenAI-compatible REST API configuration
    maas_api_base_url: str = Field(
        default_factory=lambda: _base_url
    )
    maas_api_key: str = Field(
        default_factory=lambda: _active_key
    )
    model_name: str = Field(
        default_factory=lambda: _model
    )
    embedding_model_name: str = Field(
        default_factory=lambda: _embed_model
    )

    # API Server Network Host & Port Configuration
    api_host: str = Field(
        default_factory=lambda: os.getenv("API_HOST", "0.0.0.0")
    )
    api_port: int = Field(
        default_factory=lambda: int(os.getenv("API_PORT", "8000"))
    )

    # Streamlit Server Defaults
    streamlit_server_port: int = Field(
        default_factory=lambda: int(os.getenv("STREAMLIT_SERVER_PORT", "8501"))
    )
    streamlit_server_address: str = Field(
        default_factory=lambda: os.getenv("STREAMLIT_SERVER_ADDRESS", "0.0.0.0")
    )

    # Local Offline Embedding Fallback
    local_fallback_embedding_model: str = "all-MiniLM-L6-v2"
    chunk_size: int = 450
    chunk_overlap: int = 80
    top_k_retrievals: int = 4

    # Appliance Diagnostic Platforms
    supported_hardware: list[str] = [
        "Bosch 800 Series Dishwasher (SHEM78)",
        "Whirlpool Front-Load Washer (Alpha/VMW)",
        "LG Smart French-Door Refrigerator (LFXS)",
        "Breville Dual Boiler Espresso Machine (BES920)"
    ]

    model_id_mapping: dict[str, str] = {
        "BOSCH_SHEM78": "Bosch 800 Series Dishwasher (SHEM78)",
        "WHIRLPOOL_WASHER_ALPHA": "Whirlpool Front-Load Washer (Alpha/VMW)",
        "LG_REFRIG_LFXS": "LG Smart French-Door Refrigerator (LFXS)",
        "BREVILLE_BES920": "Breville Dual Boiler Espresso Machine (BES920)"
    }


# Global Settings Instance
settings = SystemSettings()
