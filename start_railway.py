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

def setup_blockchain_dependencies():
    """Setup blockchain tool dependencies for Railway direct Python execution."""
    print("🔧 Setting up blockchain tool dependencies...")
    
    # Since Railway uses direct Python execution, we ensure critical dependencies
    # are available in the main Python environment
    
    try:
        # Test critical imports that create_market_omen.py needs
        import typer
        print("✅ typer available")
        
        import web3
        print("✅ web3 available") 
        
        import eth_account
        print("✅ eth_account available")
        
        import numpy
        print("✅ numpy available")
        
        # Google Cloud dependencies
        from google.cloud import functions_v1
        print("✅ google-cloud-functions available")
        
        from google.cloud import secretmanager
        print("✅ google-cloud-secret-manager available")
        
        print("✅ All critical blockchain dependencies available")
        return True
        
    except ImportError as e:
        print(f"⚠️ Missing dependency: {e}")
        print("📦 Installing missing dependencies...")
        
        # Install missing dependencies
        missing_packages = []
        
        try:
            import typer
        except ImportError:
            missing_packages.append("typer>=0.9.0")
            
        try:
            import web3
        except ImportError:
            missing_packages.append("web3>=6.15.1")
            
        try:
            import eth_account
        except ImportError:
            missing_packages.append("eth-account>=0.8.0")
            
        try:
            import numpy
        except ImportError:
            missing_packages.append("numpy>=1.26.4")
            
        try:
            from google.cloud import functions_v1
        except ImportError:
            missing_packages.append("google-cloud-functions>=1.16.0")
            
        try:
            from google.cloud import secretmanager
        except ImportError:
            missing_packages.append("google-cloud-secret-manager>=2.18.2")
        
        if missing_packages:
            print(f"📦 Installing: {', '.join(missing_packages)}")
            subprocess.run([
                sys.executable, "-m", "pip", "install"
            ] + missing_packages, check=True, timeout=180)
            print("✅ Missing dependencies installed")
        
        return True
        
    except Exception as e:
        print(f"⚠️ Dependency setup failed: {e}, continuing anyway...")
        return True  # Don't fail startup for dependency issues

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
    
    # Setup blockchain dependencies for direct Python execution (non-blocking)
    setup_blockchain_dependencies()
    
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