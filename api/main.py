"""
Vercel deployment entry point for the Supafund Market Creation Agent.
This file serves as the serverless function entry point.
"""
import sys
import os
import logging

# Configure logging for serverless environment
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    # Add the src directory to Python path for imports
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    src_dir = os.path.join(parent_dir, 'src')
    
    # Add gnosis_predict_market_tool to Python path
    gnosis_tool_path = os.path.join(parent_dir, 'gnosis_predict_market_tool')
    
    # Insert paths at the beginning
    sys.path.insert(0, src_dir)
    sys.path.insert(0, gnosis_tool_path)
    
    logger.info(f"Added src directory to path: {src_dir}")
    logger.info(f"Added gnosis tool to path: {gnosis_tool_path}")
    
    # Verify gnosis_predict_market_tool is accessible
    gnosis_tool_exists = os.path.exists(gnosis_tool_path)
    logger.info(f"Gnosis tool directory exists: {gnosis_tool_exists}")
    
    if gnosis_tool_exists:
        prediction_tool_path = os.path.join(gnosis_tool_path, 'prediction_market_agent_tooling')
        logger.info(f"Prediction market tooling exists: {os.path.exists(prediction_tool_path)}")
    
    # Import the FastAPI app from src/main.py  
    from main import app
    
    logger.info("Successfully imported FastAPI app")
    
except Exception as e:
    logger.error(f"Error during import: {e}")
    import traceback
    traceback.print_exc()
    
    # Create a minimal fallback app
    from fastapi import FastAPI
    app = FastAPI(title="Supafund Agent - Import Error")
    
    @app.get("/")
    async def error_info():
        return {
            "status": "error",
            "message": f"Failed to import main app: {str(e)}",
            "python_path": sys.path[:5],  # Show first 5 entries
            "current_dir": current_dir,
            "src_dir": src_dir if 'src_dir' in locals() else "undefined",
            "gnosis_tool_path": gnosis_tool_path if 'gnosis_tool_path' in locals() else "undefined"
        }

# Export the app directly for Vercel's Python runtime
# Vercel will automatically handle ASGI/WSGI requests

# For direct import compatibility
if __name__ == "__main__":
    import uvicorn
    # This allows local testing with: python api/main.py
    uvicorn.run(app, host="0.0.0.0", port=8000)