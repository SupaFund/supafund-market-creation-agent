import os
from dotenv import load_dotenv

# --- Project Root Calculation ---
# Get the directory of the current file (src/config.py)
CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))
# Get the project root directory (one level up from 'src')
PROJECT_ROOT = os.path.dirname(CONFIG_DIR)

# Load environment variables from .env file in the project root
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

class Config:
    """
    Application configuration from environment variables.
    """
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")
    OMEN_PRIVATE_KEY = os.getenv("OMEN_PRIVATE_KEY")
    POETRY_PATH = os.getenv("POETRY_PATH", "poetry") # Default to 'poetry' if not set
    
    # Resolve OMEN_SCRIPT_PROJECT_PATH to an absolute path
    _omen_script_path_raw = os.getenv("OMEN_SCRIPT_PROJECT_PATH", ".")
    if os.path.isabs(_omen_script_path_raw):
        OMEN_SCRIPT_PROJECT_PATH = _omen_script_path_raw
    else:
        OMEN_SCRIPT_PROJECT_PATH = os.path.abspath(os.path.join(PROJECT_ROOT, _omen_script_path_raw))

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
        ]
        missing_vars = [var for var in required_vars if not getattr(Config, var)]
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

# Validate configuration on import
Config.validate()
