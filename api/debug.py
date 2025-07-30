"""
Simple debug endpoint to test Vercel deployment
"""
import sys
import os
from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI(title="Debug Info")

@app.get("/")
async def debug_info():
    """Debug information endpoint"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    
    return {
        "status": "ok",
        "message": "Debug endpoint working",
        "python_version": sys.version,
        "current_dir": current_dir,
        "parent_dir": parent_dir,
        "python_path": sys.path[:10],  # First 10 entries
        "environment_vars": {
            "PYTHONPATH": os.environ.get("PYTHONPATH", "Not set"),
            "VERCEL": os.environ.get("VERCEL", "Not set")
        },
        "directory_contents": {
            "current": os.listdir(current_dir) if os.path.exists(current_dir) else "Not found",
            "parent": os.listdir(parent_dir) if os.path.exists(parent_dir) else "Not found",
            "src_exists": os.path.exists(os.path.join(parent_dir, "src")),
            "gnosis_exists": os.path.exists(os.path.join(parent_dir, "gnosis_predict_market_tool"))
        }
    }

@app.get("/test")
async def test_imports():
    """Test importing modules"""
    try:
        # Add paths
        current_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(current_dir)
        src_dir = os.path.join(parent_dir, 'src')
        sys.path.insert(0, src_dir)
        
        # Try importing
        import main as src_main
        return {
            "status": "success",
            "message": "Successfully imported src.main",
            "app_title": src_main.app.title if hasattr(src_main, 'app') else "No app found"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to import: {str(e)}",
            "error_type": type(e).__name__
        }