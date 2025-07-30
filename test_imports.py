#!/usr/bin/env python3
"""
Quick test to verify all imports are working correctly
"""

import sys

def test_import(module_name, description):
    try:
        __import__(module_name)
        print(f"✅ {description}: OK")
        return True
    except Exception as e:
        # Some modules are optional
        if "optional" in description.lower() and "xai_sdk" in module_name:
            print(f"⚠️  {description}: NOT INSTALLED (optional)")
            return True  # Count as success for optional modules
        else:
            print(f"❌ {description}: FAILED - {e}")
            return False

def main():
    print("Testing imports for Market Resolution System...")
    print("=" * 50)
    
    success_count = 0
    total_tests = 0
    
    # Test basic imports
    tests = [
        ("fastapi", "FastAPI"),
        ("uvicorn", "Uvicorn"),
        ("supabase", "Supabase client"),
        ("requests", "Requests library"),
        ("src.config", "Configuration module"),
        ("src.market_monitor", "Market monitor"),
        ("src.resolution_researcher", "Resolution researcher"),
        ("xai_sdk", "xAI SDK (optional)"),
        ("src.blockchain_resolver", "Blockchain resolver"),
        ("src.resolution_logger", "Resolution logger"),
        ("src.daily_scheduler", "Daily scheduler"),
        ("src.main", "Main FastAPI application")
    ]
    
    for module, description in tests:
        total_tests += 1
        if test_import(module, description):
            success_count += 1
    
    print("=" * 50)
    print(f"Results: {success_count}/{total_tests} imports successful")
    
    if success_count == total_tests:
        print("🎉 All imports working correctly!")
        return 0
    else:
        print("⚠️  Some imports failed. Check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())