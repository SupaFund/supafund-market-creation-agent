#!/usr/bin/env python3
"""
Local development server script for Supafund Market Creation Agent.
Sets up minimal environment variables for testing.
"""
import os
import sys
import subprocess
from pathlib import Path

def setup_minimal_env():
    """Setup minimal environment variables for local testing."""
    # Get the project root directory
    project_root = Path(__file__).parent
    
    # Set minimal required environment variables if not already set
    env_vars = {
        'SUPABASE_URL': 'https://test.supabase.co',
        'SUPABASE_KEY': 'test_key_for_local_development',
        'OMEN_PRIVATE_KEY': '0x' + '1' * 64,  # Test private key - REPLACE WITH REAL KEY FOR PRODUCTION
        'GRAPH_API_KEY': 'test_graph_api_key'  # REPLACE WITH REAL API KEY FOR PRODUCTION
    }
    
    for key, value in env_vars.items():
        if key not in os.environ:
            os.environ[key] = value
            print(f"Set {key} to test value")

def main():
    """Run the local development server."""
    print("🚀 Starting Supafund Market Creation Agent (Local Development)")
    print("="*60)
    print("🔗 REAL MODE: All blockchain transactions are real!")
    print("   ⚠️  Make sure you have sufficient funds in your wallet")
    print("-"*60)
    
    # Setup environment
    setup_minimal_env()
    
    # Check if we can import the app
    try:
        from src.main import app
        print("✅ FastAPI app imported successfully")
    except Exception as e:
        print(f"❌ Failed to import app: {e}")
        sys.exit(1)
    
    # Run the server
    try:
        import uvicorn
        print("\n🌐 Server starting at http://127.0.0.1:8000")
        print("📚 API docs available at http://127.0.0.1:8000/docs")
        print("Press Ctrl+C to stop the server\n")
        
        uvicorn.run(
            "src.main:app",
            host="127.0.0.1",
            port=8000,
            reload=True,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n👋 Server stopped")
    except Exception as e:
        print(f"❌ Server error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()