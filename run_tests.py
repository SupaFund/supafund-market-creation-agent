#!/usr/bin/env python3
"""
Test runner for the Market Resolution System
"""
import subprocess
import sys
import os
from pathlib import Path

def run_command(cmd, description, cwd=None):
    """Run a command and report results"""
    print(f"\n{'='*60}")
    print(f"🔧 {description}")
    print(f"{'='*60}")
    print(f"Command: {' '.join(cmd)}")
    print()
    
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=False,  # Show output in real-time
            text=True
        )
        
        if result.returncode == 0:
            print(f"\n✅ {description} - PASSED")
            return True
        else:
            print(f"\n❌ {description} - FAILED (exit code: {result.returncode})")
            return False
            
    except FileNotFoundError:
        print(f"\n❌ {description} - COMMAND NOT FOUND")
        return False
    except Exception as e:
        print(f"\n❌ {description} - ERROR: {e}")
        return False

def main():
    print("🧪 Market Resolution System - Test Suite Runner")
    print("=" * 60)
    
    # Get project directory
    project_dir = Path(__file__).parent
    os.chdir(project_dir)
    
    # Test results tracking
    results = []
    
    # 1. Test basic imports
    success = run_command(
        [sys.executable, "test_imports.py"],
        "Testing Basic Imports"
    )
    results.append(("Import Tests", success))
    
    # 2. Install test dependencies (if needed)
    print(f"\n{'='*60}")
    print("📦 Installing Test Dependencies")
    print(f"{'='*60}")
    
    test_deps = [
        "pytest", "pytest-asyncio", "pytest-mock", "pytest-cov", 
        "httpx", "factory-boy", "freezegun", "responses"
    ]
    
    for dep in test_deps:
        try:
            __import__(dep.replace('-', '_'))
            print(f"✅ {dep} already installed")
        except ImportError:
            print(f"⚠️  Installing {dep}...")
            result = subprocess.run([sys.executable, "-m", "pip", "install", dep], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✅ {dep} installed successfully")
            else:
                print(f"❌ Failed to install {dep}")
    
    # 3. Run unit tests
    success = run_command(
        [sys.executable, "-m", "pytest", "tests/unit/", "-v", "--tb=short"],
        "Running Unit Tests"
    )
    results.append(("Unit Tests", success))
    
    # 4. Run integration tests
    success = run_command(
        [sys.executable, "-m", "pytest", "tests/integration/", "-v", "--tb=short"],
        "Running Integration Tests"
    )
    results.append(("Integration Tests", success))
    
    # 5. Run tests with coverage (if pytest-cov is available)
    try:
        import pytest_cov
        success = run_command(
            [sys.executable, "-m", "pytest", "tests/", "--cov=src", "--cov-report=term-missing", "--cov-report=html"],
            "Running Tests with Coverage"
        )
        results.append(("Coverage Tests", success))
    except ImportError:
        print("\n⚠️  Skipping coverage tests (pytest-cov not available)")
    
    # 6. Run specific test categories
    test_categories = [
        ("tests/unit/test_market_monitor.py", "Market Monitor Tests"),
        ("tests/unit/test_resolution_researcher.py", "Resolution Researcher Tests"), 
        ("tests/unit/test_blockchain_resolver.py", "Blockchain Resolver Tests"),
        ("tests/unit/test_resolution_logger.py", "Resolution Logger Tests"),
        ("tests/unit/test_edge_cases.py", "Edge Cases Tests"),
    ]
    
    for test_path, description in test_categories:
        if Path(test_path).exists():
            success = run_command(
                [sys.executable, "-m", "pytest", test_path, "-v"],
                f"Running {description}"
            )
            results.append((description, success))
    
    # 7. Test API endpoints (if server can start)
    try:
        print(f"\n{'='*60}")
        print("🌐 Testing API Server Startup")
        print(f"{'='*60}")
        
        # Try to start server briefly to test
        import multiprocessing
        import time
        import requests
        
        def start_server():
            os.system(f"{sys.executable} -m uvicorn src.main:app --port 8999 --host 127.0.0.1")
        
        # Start server in background
        server_process = multiprocessing.Process(target=start_server)
        server_process.start()
        
        # Wait for server to start
        time.sleep(3)
        
        try:
            response = requests.get("http://127.0.0.1:8999/", timeout=5)
            if response.status_code == 200:
                print("✅ API Server - STARTED SUCCESSFULLY")
                results.append(("API Server Startup", True))
            else:
                print(f"⚠️  API Server - Started but returned status {response.status_code}")
                results.append(("API Server Startup", False))
        except requests.exceptions.RequestException as e:
            print(f"❌ API Server - CONNECTION FAILED: {e}")
            results.append(("API Server Startup", False))
        finally:
            server_process.terminate()
            server_process.join(timeout=5)
            if server_process.is_alive():
                server_process.kill()
                
    except Exception as e:
        print(f"❌ API Server Test - ERROR: {e}")
        results.append(("API Server Startup", False))
    
    # 8. Summary
    print(f"\n{'='*60}")
    print("📊 TEST RESULTS SUMMARY")
    print(f"{'='*60}")
    
    passed = 0
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{test_name:<30} {status}")
        if success:
            passed += 1
    
    print(f"\n{'='*60}")
    print(f"🎯 OVERALL RESULTS: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! System is ready for production.")
        return 0
    else:
        print("⚠️  Some tests failed. Please review the output above.")
        return 1

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n🛑 Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n💥 Unexpected error: {e}")
        sys.exit(1)