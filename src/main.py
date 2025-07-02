from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel, Field
import logging

from .supabase_client import get_application_details
from .omen_creator import create_omen_market

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Supafund Market Creation Agent",
    description="An agent to create prediction markets on Omen for Supafund applications.",
    version="1.0.0"
)

class MarketCreationRequest(BaseModel):
    application_id: str = Field(..., 
        description="The UUID of the application in Supafund.",
        examples=["a1b2c3d4-e5f6-7890-1234-567890abcdef"]
    )

@app.get("/", tags=["Health Check"])
async def read_root():
    """
    Root endpoint for health checks.
    """
    return {"status": "ok", "message": "Supafund Market Creation Agent is running."}


@app.post("/create-market", tags=["Market Creation"])
async def handle_create_market(request: MarketCreationRequest):
    """
    Receives a request to create a prediction market for a given application.
    """
    application_id = request.application_id
    logger.info(f"Received request to create market for application_id: {application_id}")

    # 1. Fetch application details from Supabase
    logger.info(f"Fetching details for application {application_id}...")
    application_details = get_application_details(application_id)

    if not application_details:
        logger.error(f"Application with id {application_id} not found.")
        raise HTTPException(
            status_code=404,
            detail=f"Application with id {application_id} not found.",
        )

    # 2. Trigger Omen market creation
    logger.info(f"Triggering Omen market creation for application {application_id}...")
    success, message = create_omen_market(application_details)

    if not success:
        logger.error(f"Failed to create market for application {application_id}: {message}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create market: {message}",
        )

    logger.info(f"Successfully created market for application {application_id}.")
    return {
        "status": "success",
        "message": "Market creation process initiated successfully.",
        "application_id": application_id,
        "omen_creation_output": message,
    }
