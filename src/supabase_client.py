from supabase import create_client, Client
import time
from .config import Config

def get_supabase_client() -> Client:
    """
    Initializes and returns the Supabase client.
    """
    return create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)

def get_application_details(application_id: str, max_retries: int = 3, delay_seconds: int = 1) -> dict | None:
    """
    Fetches application details from Supabase with a retry mechanism.

    Args:
        application_id: The UUID of the program application.
        max_retries: The maximum number of times to retry the request.
        delay_seconds: The number of seconds to wait between retries.

    Returns:
        A dictionary with application details or None if not found or failed.
    """
    supabase = get_supabase_client()
    
    query = (
        supabase.table("program_applications")
        .select(
            """
            id,
            project:projects (
                name
            ),
            program:funding_programs (
                name,
                application_deadline_date
            )
            """
        )
        .eq("id", application_id)
        .single()
    )
    
    last_exception = None
    for attempt in range(max_retries):
        try:
            response = query.execute()
            
            if not response.data:
                # This means the query was successful but found no data.
                # No need to retry in this case.
                return None

            # Flatten the structure for easier use
            application_data = response.data
            details = {
                "application_id": application_data.get("id"),
                "project_name": application_data.get("project", {}).get("name"),
                "program_name": application_data.get("program", {}).get("name"),
                "deadline": application_data.get("program", {}).get("application_deadline_date"),
            }

            if not all([details["project_name"], details["program_name"]]):
                print(f"Warning: Missing project_name or program_name for application {application_id}")
            
            # Success, return the details immediately
            return details

        except Exception as e:
            last_exception = e
            print(f"Attempt {attempt + 1}/{max_retries} failed: {e}")
            if attempt < max_retries - 1:
                print(f"Retrying in {delay_seconds} second(s)...")
                time.sleep(delay_seconds)
            else:
                print("All retry attempts failed.")

    # If all retries failed, log the final error and return None
    if last_exception:
        print(f"Error fetching application details from Supabase after {max_retries} attempts: {last_exception}")

    return None
