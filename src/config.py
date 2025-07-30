import os
from dotenv import load_dotenv

# --- Project Root Calculation ---
# Get the directory of the current file (src/config.py)
CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))
# Get the project root directory (one level up from 'src')
PROJECT_ROOT = os.path.dirname(CONFIG_DIR)

# Load environment variables from .env file in the project root
env_file_path = os.path.join(PROJECT_ROOT, '.env')
load_dotenv(env_file_path, override=True)

class Config:
    """
    Application configuration from environment variables.
    """
    # Existing configuration
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")
    OMEN_PRIVATE_KEY = os.getenv("OMEN_PRIVATE_KEY")
    GRAPH_API_KEY = os.getenv("GRAPH_API_KEY")
    POETRY_PATH = os.getenv("POETRY_PATH", "poetry") # Default to 'poetry' if not set
    
    # New configuration for market resolution system
    XAI_API_KEY = os.getenv("XAI_API_KEY")  # Grok API key
    
    # Email configuration
    SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME = os.getenv("SMTP_USERNAME")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
    ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")
    FROM_EMAIL = os.getenv("FROM_EMAIL")
    
    # Resolution system configuration
    MIN_RESEARCH_CONFIDENCE = float(os.getenv("MIN_RESEARCH_CONFIDENCE", "0.7"))
    MAX_MARKETS_PER_RUN = int(os.getenv("MAX_MARKETS_PER_RUN", "10"))
    RESOLUTION_DELAY_SECONDS = int(os.getenv("RESOLUTION_DELAY_SECONDS", "30"))
    
    # Blockchain interaction configuration (for gnosis_predict_market_tool)
    GNOSIS_RPC_URL = os.getenv("GNOSIS_RPC_URL", "https://rpc.gnosischain.com")
    TRANSACTION_TIMEOUT = int(os.getenv("TRANSACTION_TIMEOUT", "300"))  # 5 minutes
    
    # Resolve OMEN_SCRIPT_PROJECT_PATH to an absolute path
    _omen_script_path_raw = os.getenv("OMEN_SCRIPT_PROJECT_PATH", ".")
    if os.path.isabs(_omen_script_path_raw):
        OMEN_SCRIPT_PROJECT_PATH = _omen_script_path_raw
    else:
        OMEN_SCRIPT_PROJECT_PATH = os.path.abspath(os.path.join(PROJECT_ROOT, _omen_script_path_raw))

    PROJECT_ROOT = PROJECT_ROOT  # Make available to other modules

    @staticmethod
    def validate():
        """
        Validates that all necessary environment variables are set.
        Raises ValueError if a required variable is missing.
        """
        required_vars = [
            "SUPABASE_URL",
            "SUPABASE_KEY",
            "OMEN_PRIVATE_KEY",
            "GRAPH_API_KEY",
        ]
        missing_vars = [var for var in required_vars if not getattr(Config, var)]
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
        
        # Warn about optional but recommended variables
        recommended_vars = [
            "XAI_API_KEY",
            "ADMIN_EMAIL",
            "SMTP_USERNAME",
            "SMTP_PASSWORD"
        ]
        missing_recommended = [var for var in recommended_vars if not getattr(Config, var)]
        if missing_recommended:
            import warnings
            warnings.warn(f"Recommended environment variables not set: {', '.join(missing_recommended)}")

# Validate configuration on import
Config.validate()
