import logging
import time

from src.supabase_client import get_supabase_client, fetch_and_lock_job, get_application_details, update_job_status
from src.omen_creator import create_omen_market

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

POLL_INTERVAL = 10  # seconds

def main():
    """Main function to run the market creation agent."""
    logging.info("Starting Supafund Market Creation Agent...")
    supabase = get_supabase_client()

    while True:
        try:
            job = fetch_and_lock_job(supabase)
            if job:
                try:
                    application_id = job.get("application_id")
                    if not application_id:
                        raise ValueError("Job is missing application_id")

                    logging.info(f"Processing application_id: {application_id}")
                    application_details = get_application_details(supabase, application_id)
                    if not application_details:
                        raise ValueError(f"Could not retrieve details for application {application_id}")

                    market_result = create_omen_market(application_details)

                    update_job_status(supabase, job["id"], "completed", result=market_result)
                    logging.info(f"Successfully processed job {job['id']}.")

                except Exception as e:
                    error_message = f"Failed to process job {job['id']}: {e}"
                    logging.error(error_message)
                    update_job_status(supabase, job["id"], "error", error_message=error_message)
            else:
                logging.info(f"No pending jobs. Waiting for {POLL_INTERVAL} seconds...")
        
        except Exception as e:
            logging.error(f"An error occurred in the main loop: {e}")

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
