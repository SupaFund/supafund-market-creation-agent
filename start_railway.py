#!/usr/bin/env python3
"""
Railway startup script for Supafund Market Creation Agent.
Handles dynamic configuration and environment setup specifically for Railway platform.
"""
import os
import sys
import uvicorn
from src.config import Config
from src.railway_logger import market_logger

def setup_railway_environment():
    """Setup Railway-specific environment variables and logging."""
    
    # Ensure critical environment variables are set
    os.environ.setdefault("PYTHONPATH", ".")
    os.environ.setdefault("PYTHONUNBUFFERED", "1")
    
    # Railway detection and logging
    railway_info = {
        "environment": os.getenv("RAILWAY_ENVIRONMENT", "unknown"),
        "service": os.getenv("RAILWAY_SERVICE_NAME", "supafund-agent"),
        "project": os.getenv("RAILWAY_PROJECT_NAME", "unknown"),
        "deployment_id": os.getenv("RAILWAY_DEPLOYMENT_ID", "unknown"),
    }
    
    print("🚂 Railway Environment Setup:")
    for key, value in railway_info.items():
        print(f"  {key}: {value}")
    
    # Log startup to Railway logger
    market_logger.log_railway_startup(
        str(Config.PORT), 
        Config.HOST, 
        railway_info["service"]
    )
    
    return railway_info

def validate_dependencies():
    """Validate that critical dependencies are available."""
    print("\n🔍 Dependency Validation:")
    
    # Check gnosis_predict_market_tool
    gnosis_path = "gnosis_predict_market_tool"
    if os.path.exists(gnosis_path):
        print(f"  ✅ gnosis_predict_market_tool found at {gnosis_path}")
    else:
        print(f"  ❌ gnosis_predict_market_tool not found at {gnosis_path}")
        return False
    
    # Check poetry availability
    try:
        import subprocess
        result = subprocess.run([Config.POETRY_PATH, "--version"], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print(f"  ✅ Poetry available: {result.stdout.strip()}")
        else:
            print(f"  ⚠️ Poetry check failed: {result.stderr.strip()}")
    except Exception as e:
        print(f"  ⚠️ Poetry validation error: {e}")
    
    # Test subprocess modules
    try:
        from src.omen_subprocess_creator import OmenSubprocessCreator
        creator = OmenSubprocessCreator()
        print(f"  ✅ Subprocess creator initialized (direct_python: {creator.use_direct_python})")
    except Exception as e:
        print(f"  ❌ Subprocess creator error: {e}")
        return False
    
    return True

def main():
    """Main startup function for Railway deployment."""
    
    print("🚂 Starting Supafund Market Creation Agent on Railway")
    print("=" * 60)
    
    # Setup Railway environment
    railway_info = setup_railway_environment()
    
    # Validate dependencies
    if not validate_dependencies():
        print("❌ Dependency validation failed!")
        sys.exit(1)
    
    # Configuration summary
    print(f"\n🌐 Server Configuration:")
    print(f"  Host: {Config.HOST}")
    print(f"  Port: {Config.PORT}")
    print(f"  Environment: {Config.RAILWAY_ENVIRONMENT}")
    print(f"  Railway Detection: {Config.IS_RAILWAY}")
    
    print("\n🚀 Starting FastAPI server...")
    print("=" * 60)
    
    try:
        # Start the application with Railway-optimized settings
        uvicorn.run(
            "src.main:app",
            host=Config.HOST,
            port=Config.PORT,
            log_level="info",
            access_log=True,
            # Railway-specific optimizations
            workers=1,  # Single worker for Railway's resource model
            timeout_keep_alive=120,  # Extended keep-alive for Railway
            # Performance optimizations
            loop="uvloop" if os.name != 'nt' else "asyncio",
            http="httptools",
        )
    except Exception as e:
        print(f"❌ Failed to start application: {e}")
        market_logger.log_error("startup_failure", str(e), "system")
        sys.exit(1)

if __name__ == "__main__":
    main()