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


class SystemSettings(BaseModel):
    """
    Enterprise system configuration parameters.
    Default configurations match the TCS GenAI Lab MaaS OpenAI-compatible gateway.
    """
    app_name: str = "AI Product Manual Troubleshooting Assistant"
    app_version: str = "1.0.0"
    
    # Model-as-a-Service (MaaS) OpenAI-compatible REST API configuration
    maas_api_base_url: str = Field(
        default_factory=lambda: os.getenv("MAAS_API_BASE_URL", "https://genailab.tcs.in/v1").rstrip("/")
    )
    maas_api_key: str = Field(
        default_factory=lambda: os.getenv("MAAS_API_KEY", "")
    )
    model_name: str = Field(
        default_factory=lambda: os.getenv("MODEL_NAME", "azure/genailab-maas-gpt-4o-mini")
    )
    embedding_model_name: str = Field(
        default_factory=lambda: os.getenv("EMBEDDING_MODEL_NAME", "azure/genailab-maas-text-embedding-3-large")
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

    # Corporate IT Supported Hardware
    supported_hardware: list[str] = [
        "Apex Router Pro-X",
        "CoreSwitch 4000"
    ]


# Global Settings Instance
settings = SystemSettings()
