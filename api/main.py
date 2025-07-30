"""
Vercel deployment entry point for the Supafund Market Creation Agent.
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

# Add paths for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
src_dir = os.path.join(parent_dir, 'src')
gnosis_tool_path = os.path.join(parent_dir, 'gnosis_predict_market_tool')

# Insert paths at the beginning
sys.path.insert(0, src_dir)
sys.path.insert(0, gnosis_tool_path)

logger.info(f"Added src directory to path: {src_dir}")
logger.info(f"Added gnosis tool to path: {gnosis_tool_path}")

try:
    # Import the FastAPI app from src/main.py  
    from src.main import app
    logger.info("Successfully imported FastAPI app")
    
    # Add a simple health check to test if the app is working
    @app.get("/health")
    async def health_check():
        return {
            "status": "ok",
            "message": "Supafund Market Creation Agent is running on Vercel",
            "paths": {
                "src_dir": src_dir,
                "gnosis_tool_path": gnosis_tool_path,
                "src_exists": os.path.exists(src_dir),
                "gnosis_exists": os.path.exists(gnosis_tool_path)
            }
        }
    
except ImportError as e:
    logger.error(f"Import error: {e}")
    import traceback
    traceback.print_exc()
    
    # Create a minimal fallback app with error info
    from fastapi import FastAPI
    app = FastAPI(title="Supafund Agent - Import Error")
    
    @app.get("/")
    async def error_info():
        return {
            "status": "error",
            "message": f"Failed to import main app: {str(e)}",
            "error_type": type(e).__name__,
            "python_path": sys.path[:10],
            "paths": {
                "current_dir": current_dir,
                "src_dir": src_dir,
                "gnosis_tool_path": gnosis_tool_path,
                "src_exists": os.path.exists(src_dir),
                "gnosis_exists": os.path.exists(gnosis_tool_path)
            }
        }
    
    @app.get("/health")
    async def health_error():
        return {"status": "error", "message": "App failed to start properly"}

except Exception as e:
    logger.error(f"Unexpected error: {e}")
    import traceback
    traceback.print_exc()
    
    from fastapi import FastAPI
    app = FastAPI(title="Supafund Agent - Unexpected Error")
    
    @app.get("/")
    async def unexpected_error():
        return {
            "status": "error",
            "message": f"Unexpected error: {str(e)}",
            "error_type": type(e).__name__
        }

# Export the app variable for Vercel