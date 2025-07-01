import logging
from supabase import create_client, Client
from src.config import SUPABASE_URL, SUPABASE_KEY, AGENT_ID

logging.basicConfig(level=logging.INFO)

def get_supabase_client() -> Client:
    """Initializes and returns the Supabase client."""
    return create_client(SUPABASE_URL, SUPABASE_KEY)

def fetch_and_lock_job(supabase: Client):
    """
    Fetches a pending 'market' job and locks it for processing.
    It uses a database function `get_and_lock_job` to ensure atomicity.
    """
    try:
        res = supabase.rpc("get_and_lock_job", {"agent_type_arg": "market", "locking_agent_id_arg": AGENT_ID}).execute()
        if res.data:
            job = res.data[0]
            logging.info(f"Locked job {job['id']} for processing.")
            return job
        else:
            logging.info("No pending market creation jobs found.")
            return None
    except Exception as e:
        logging.error(f"Error fetching and locking job: {e}")
        return None

def get_application_details(supabase: Client, application_id: str):
    """Fetches details for a specific application and its related project."""
    try:
        res = supabase.table("program_applications").select("*, projects(*)").eq("id", application_id).single().execute()
        return res.data
    except Exception as e:
        logging.error(f"Error fetching application details for {application_id}: {e}")
        return None

def update_job_status(supabase: Client, job_id: str, status: str, result: dict = None, error_message: str = None):
    """Updates the status of a job."""
    update_data = {"status": status}
    if status == "completed":
        update_data["completed_at"] = "now()"
        update_data["result"] = result
    elif status == "error":
        update_data["failed_at"] = "now()"
        update_data["error"] = error_message
    
    try:
        supabase.table("agent_jobs").update(update_data).eq("id", job_id).execute()
        logging.info(f"Updated job {job_id} status to {status}.")
    except Exception as e:
        logging.error(f"Error updating job {job_id} status: {e}")
