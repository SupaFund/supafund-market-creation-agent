#!/usr/bin/env python3
"""
Railway startup script for Supafund Market Creation Agent.
Handles Poetry dependencies and environment setup specifically for Railway platform.
"""
import os
import sys
import subprocess
import uvicorn
from src.config import Config
from src.railway_logger import market_logger

def setup_poetry_dependencies():
    """Setup Poetry dependencies for gnosis_predict_market_tool."""
    print("🔧 Setting up Poetry dependencies...")
    
    gnosis_path = "gnosis_predict_market_tool"
    if not os.path.exists(gnosis_path):
        print(f"⚠️ {gnosis_path} directory not found, skipping Poetry setup")
        return True
    
    try:
        # Check if poetry is available
        result = subprocess.run(["poetry", "--version"], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            print("📦 Installing Poetry...")
            subprocess.run([sys.executable, "-m", "pip", "install", "poetry"], 
                         check=True, timeout=60)
        
        # Install dependencies
        print(f"📚 Installing dependencies in {gnosis_path}...")
        result = subprocess.run(["poetry", "install", "--no-dev", "--no-root"], 
                              cwd=gnosis_path, timeout=300)
        
        if result.returncode == 0:
            print("✅ Poetry dependencies installed successfully")
            return True
        else:
            print("⚠️ Poetry install had issues, but continuing...")
            return True  # Don't fail startup for Poetry issues
            
    except Exception as e:
        print(f"⚠️ Poetry setup failed: {e}, continuing anyway...")
        return True  # Don't fail startup for Poetry issues

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

def validate_core_dependencies():
    """Validate that core dependencies are available."""
    print("\n🔍 Core Dependency Validation:")
    
    # Check subprocess modules
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
    
    # Setup Poetry dependencies (non-blocking)
    setup_poetry_dependencies()
    
    # Validate core dependencies
    if not validate_core_dependencies():
        print("❌ Core dependency validation failed!")
        # Don't exit, let Railway restart handle this
        
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