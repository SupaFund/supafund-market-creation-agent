#!/usr/bin/env python3
"""
Simple script to start the FastAPI server and test basic functionality
"""

import asyncio
import subprocess
import sys
import time
import requests
from pathlib import Path

def start_server():
    """Start the uvicorn server"""
    print("🚀 Starting FastAPI server...")
    
    # Change to project directory
    project_dir = Path(__file__).parent
    
    # Start uvicorn server
    cmd = [
        sys.executable, 
        "-m", "uvicorn", 
        "src.main:app", 
        "--host", "127.0.0.1",
        "--port", "8000",
        "--reload"
    ]
    
    print(f"Running: {' '.join(cmd)}")
    process = subprocess.Popen(cmd, cwd=project_dir)
    
    # Wait a bit for server to start
    print("⏳ Waiting for server to start...")
    time.sleep(3)
    
    # Test the server
    try:
        response = requests.get("http://127.0.0.1:8000/", timeout=5)
        if response.status_code == 200:
            print("✅ Server is running successfully!")
            print("📡 Available endpoints:")
            print("   - http://127.0.0.1:8000/ (Health check)")
            print("   - http://127.0.0.1:8000/docs (API documentation)")
            print("   - http://127.0.0.1:8000/resolution-status (Resolution system status)")
            print("   - http://127.0.0.1:8000/run-daily-resolution (Trigger resolution cycle)")
            print("\n💡 Visit http://127.0.0.1:8000/docs to see all available endpoints")
        else:
            print(f"⚠️  Server responded with status {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Could not connect to server: {e}")
    
    print("\n🛑 Press Ctrl+C to stop the server")
    
    try:
        # Keep the script running
        process.wait()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down server...")
        process.terminate()
        process.wait()

if __name__ == "__main__":
    start_server()