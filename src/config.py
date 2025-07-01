import os
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GNOSIS_RPC_URL = os.getenv("GNOSIS_RPC_URL")
OMEN_CREATOR_PRIVATE_KEY = os.getenv("OMEN_CREATOR_PRIVATE_KEY")
AGENT_ID = os.getenv("AGENT_ID", "market-creation-agent-v1")
