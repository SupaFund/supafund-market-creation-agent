from supabase import create_client, Client
import time
import logging
from .config import Config

logger = logging.getLogger(__name__)

def get_supabase_client() -> Client:
    """
    Initializes and returns the Supabase client.
    """
    return create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)

def test_database_connection():
    """
    Test database connection and explore table structure.
    """
    try:
        supabase = get_supabase_client()
        logger.info("Testing database connection...")
        
        # Test basic connection by trying to query program_applications table
        result = supabase.table("program_applications").select("*").limit(1).execute()
        logger.info(f"Connection test successful. Sample data: {result.data}")
        
        # Check if we can access related tables
        try:
            projects_result = supabase.table("projects").select("*").limit(1).execute()
            logger.info(f"Projects table accessible. Sample: {projects_result.data}")
        except Exception as e:
            logger.error(f"Projects table error: {e}")
            
        try:
            programs_result = supabase.table("funding_programs").select("*").limit(1).execute()
            logger.info(f"Funding programs table accessible. Sample: {programs_result.data}")
        except Exception as e:
            logger.error(f"Funding programs table error: {e}")
            
        return True
        
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        return False

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
    
    logger.info(f"Looking for application_id: {application_id}")
    
    # Test database connection first
    if not test_database_connection():
        logger.error("Database connection test failed")
        return None
    
    # First, let's try a simple query to see if the application exists at all
    try:
        simple_response = supabase.table("program_applications").select("id").eq("id", application_id).execute()
        logger.info(f"Simple query result: {simple_response.data}")
        
        if not simple_response.data:
            logger.warning(f"Application {application_id} not found in program_applications table")
            return None
            
    except Exception as e:
        logger.error(f"Simple query failed: {e}")
        return None
    
    # Now try the full query with joins
    query = (
        supabase.table("program_applications")
        .select(
            """
            id,
            project:projects (
                name,
                description
            ),
            program:funding_programs (
                name,
                application_deadline_date,
                long_description
            )
            """
        )
        .eq("id", application_id)
        .single()
    )
    
    last_exception = None
    for attempt in range(max_retries):
        try:
            logger.info(f"Executing full query, attempt {attempt + 1}")
            response = query.execute()
            logger.info(f"Query response: {response}")
            
            if not response.data:
                # This means the query was successful but found no data.
                # No need to retry in this case.
                logger.warning(f"Full query returned no data for application {application_id}")
                return None

            # Flatten the structure for easier use
            application_data = response.data
            details = {
                "application_id": application_data.get("id"),
                "project_name": application_data.get("project", {}).get("name"),
                "project_description": application_data.get("project", {}).get("description"),
                "program_description": application_data.get("program", {}).get("long_description"),
                "program_name": application_data.get("program", {}).get("name"),
                "deadline": application_data.get("program", {}).get("application_deadline_date"),
            }

            if not all([details["project_name"], details["program_name"]]):
                print(f"Warning: Missing project_name or program_name for application {application_id}")
            
            # Success, return the details immediately
            return details

        except Exception as e:
            last_exception = e
            logger.error(f"Attempt {attempt + 1}/{max_retries} failed: {e}")
            logger.error(f"Exception type: {type(e)}")
            logger.error(f"Exception details: {str(e)}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {delay_seconds} second(s)...")
                time.sleep(delay_seconds)
            else:
                logger.error("All retry attempts failed.")

    # If all retries failed, log the final error and return None
    if last_exception:
        logger.error(f"Error fetching application details from Supabase after {max_retries} attempts: {last_exception}")

    return None


def check_existing_market(application_id: str) -> dict | None:
    """
    Check if a market already exists for the given application.
    
    Args:
        application_id: The UUID of the program application.
        
    Returns:
        A dictionary with market details or None if not found.
    """
    try:
        supabase = get_supabase_client()
        
        logger.info(f"Checking for existing market for application {application_id}")
        
        response = supabase.table("prediction_markets").select("*").eq("application_id", application_id).execute()
        
        if response.data:
            market_data = response.data[0]
            logger.info(f"Found existing market: {market_data.get('market_id')}")
            return market_data
        
        logger.info(f"No existing market found for application {application_id}")
        return None
        
    except Exception as e:
        logger.error(f"Error checking existing market for application {application_id}: {e}")
        return None


def create_market_record(application_id: str, market_data: dict) -> bool:
    """
    Create a new market record in the prediction_markets table.
    
    Args:
        application_id: The UUID of the program application.
        market_data: Dictionary containing market information.
        
    Returns:
        Boolean indicating success.
    """
    try:
        supabase = get_supabase_client()
        
        logger.info(f"Creating market record for application {application_id}")
        
        record = {
            "application_id": application_id,
            "market_id": market_data.get("market_id", ""),
            "market_title": market_data.get("market_title", ""),
            "market_url": market_data.get("market_url", ""),
            "market_question": market_data.get("market_question", ""),
            "closing_time": market_data.get("closing_time"),
            "initial_funds_usd": market_data.get("initial_funds_usd", 0.01),
            "omen_creation_output": market_data.get("omen_creation_output", ""),
            "status": "created",
            "metadata": market_data.get("metadata", {})
        }
        
        response = supabase.table("prediction_markets").insert(record).execute()
        
        if response.data:
            logger.info(f"Successfully created market record: {response.data[0]['id']}")
            return True
        else:
            logger.error(f"Failed to create market record - no data returned")
            return False
            
    except Exception as e:
        logger.error(f"Error creating market record for application {application_id}: {e}")
        return False


def update_market_record(application_id: str, market_data: dict) -> bool:
    """
    Update an existing market record in the prediction_markets table.
    
    Args:
        application_id: The UUID of the program application.
        market_data: Dictionary containing updated market information.
        
    Returns:
        Boolean indicating success.
    """
    try:
        supabase = get_supabase_client()
        
        logger.info(f"Updating market record for application {application_id}")
        
        update_data = {}
        if "status" in market_data:
            update_data["status"] = market_data["status"]
        if "metadata" in market_data:
            update_data["metadata"] = market_data["metadata"]
        if "omen_creation_output" in market_data:
            update_data["omen_creation_output"] = market_data["omen_creation_output"]
            
        response = supabase.table("prediction_markets").update(update_data).eq("application_id", application_id).execute()
        
        if response.data:
            logger.info(f"Successfully updated market record for application {application_id}")
            return True
        else:
            logger.error(f"Failed to update market record - no data returned")
            return False
            
    except Exception as e:
        logger.error(f"Error updating market record for application {application_id}: {e}")
        return False


def get_market_by_application_id(application_id: str) -> dict | None:
    """
    Get market details by application ID.
    
    Args:
        application_id: The UUID of the program application.
        
    Returns:
        A dictionary with market details or None if not found.
    """
    try:
        supabase = get_supabase_client()
        
        response = supabase.table("prediction_markets").select("*").eq("application_id", application_id).single().execute()
        
        if response.data:
            return response.data
        
        return None
        
    except Exception as e:
        logger.error(f"Error getting market for application {application_id}: {e}")
        return None


def get_all_markets(status: str = None, limit: int = 100) -> list:
    """
    Get all markets, optionally filtered by status.
    
    Args:
        status: Optional status filter.
        limit: Maximum number of records to return.
        
    Returns:
        List of market records.
    """
    try:
        supabase = get_supabase_client()
        
        query = supabase.table("prediction_markets").select("*").limit(limit).order("created_at", desc=True)
        
        if status:
            query = query.eq("status", status)
            
        response = query.execute()
        
        return response.data if response.data else []
        
    except Exception as e:
        logger.error(f"Error getting markets: {e}")
        return []
