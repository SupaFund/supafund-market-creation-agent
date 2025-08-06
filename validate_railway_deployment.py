#!/usr/bin/env python3
"""
Railway deployment validation script.
Comprehensive validation of Railway deployment readiness to avoid previous deployment issues.
"""
import os
import sys
import subprocess
import json
from pathlib import Path

class RailwayValidationError(Exception):
    """Custom exception for validation failures."""
    pass

def validate_file_exists(file_path: str, description: str) -> bool:
    """Validate that a required file exists."""
    if os.path.exists(file_path):
        print(f"✅ {description}: {file_path}")
        return True
    else:
        print(f"❌ {description} MISSING: {file_path}")
        return False

def validate_file_content(file_path: str, expected_content: str, description: str) -> bool:
    """Validate that a file contains expected content."""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        if expected_content in content:
            print(f"✅ {description}: Content validated")
            return True
        else:
            print(f"❌ {description}: Expected content not found")
            return False
    except FileNotFoundError:
        print(f"❌ {description}: File not found - {file_path}")
        return False

def validate_imports() -> bool:
    """Validate that critical imports work correctly."""
    print("\n🔍 Import Validation:")
    success = True
    
    # Test config import
    try:
        from src.config import Config
        print(f"✅ Config import successful")
        print(f"  - Railway detection: {Config.IS_RAILWAY}")
        print(f"  - Host: {Config.HOST}")
        print(f"  - Port: {Config.PORT}")
    except Exception as e:
        print(f"❌ Config import failed: {e}")
        success = False
    
    # Test logger import
    try:
        from src.railway_logger import market_logger
        print(f"✅ Railway logger import successful")
    except Exception as e:
        print(f"❌ Railway logger import failed: {e}")
        success = False
    
    # Test subprocess modules
    try:
        from src.omen_subprocess_creator import OmenSubprocessCreator
        creator = OmenSubprocessCreator()
        print(f"✅ Subprocess creator import successful (use_direct_python: {creator.use_direct_python})")
    except Exception as e:
        print(f"❌ Subprocess creator import failed: {e}")
        success = False
    
    return success

def validate_poetry_setup() -> bool:
    """Validate Poetry setup in gnosis_predict_market_tool."""
    print("\n🎭 Poetry Validation:")
    
    # Check if gnosis_predict_market_tool exists
    gnosis_path = "gnosis_predict_market_tool"
    if not os.path.exists(gnosis_path):
        print(f"❌ gnosis_predict_market_tool directory not found")
        return False
    
    # Check pyproject.toml
    pyproject_path = os.path.join(gnosis_path, "pyproject.toml")
    if not os.path.exists(pyproject_path):
        print(f"❌ pyproject.toml not found in {gnosis_path}")
        return False
    print(f"✅ pyproject.toml found")
    
    # Try poetry command
    try:
        result = subprocess.run(["poetry", "--version"], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print(f"✅ Poetry available: {result.stdout.strip()}")
        else:
            print(f"❌ Poetry command failed: {result.stderr.strip()}")
            return False
    except Exception as e:
        print(f"❌ Poetry validation error: {e}")
        return False
    
    # Test poetry in gnosis directory
    try:
        result = subprocess.run(["poetry", "env", "info", "--path"],
                              cwd=gnosis_path, capture_output=True, text=True, timeout=15)
        if result.returncode == 0:
            print(f"✅ Poetry environment in gnosis_predict_market_tool: Ready")
        else:
            print(f"⚠️ Poetry environment may need setup: {result.stderr.strip()}")
    except Exception as e:
        print(f"⚠️ Poetry environment check failed: {e}")
    
    return True

def validate_requirements() -> bool:
    """Validate requirements.txt is Railway-compatible."""
    print("\n📦 Requirements Validation:")
    
    try:
        with open("requirements.txt", 'r') as f:
            content = f.read()
        
        # Check for problematic dependencies that caused previous failures
        problematic_deps = [
            "docker",  # Docker-related deps
            "kubernetes",  # K8s deps
            "--index-url",  # Custom PyPI mirrors that caused timeouts
            "pypi.tuna.tsinghua.edu.cn",  # Chinese mirror
        ]
        
        has_problems = False
        for dep in problematic_deps:
            if dep in content:
                print(f"❌ Problematic dependency found: {dep}")
                has_problems = True
        
        if not has_problems:
            print("✅ No problematic dependencies detected")
        
        # Check for Railway compatibility indicator
        if "Railway" in content or "railway" in content:
            print("✅ Requirements marked for Railway deployment")
        else:
            print("⚠️ Requirements not explicitly marked for Railway")
        
        return not has_problems
        
    except FileNotFoundError:
        print("❌ requirements.txt not found")
        return False

def validate_environment_variables() -> bool:
    """Validate critical environment variables for Railway."""
    print("\n🌍 Environment Variables Validation:")
    
    # Check for any existing critical env vars (for testing)
    critical_vars = [
        "SUPABASE_URL",
        "SUPABASE_KEY", 
        "OMEN_PRIVATE_KEY",
        "GRAPH_API_KEY"
    ]
    
    missing_vars = []
    for var in critical_vars:
        if os.getenv(var):
            print(f"✅ {var}: Set")
        else:
            print(f"⚠️ {var}: Not set (will need to be configured in Railway)")
            missing_vars.append(var)
    
    if missing_vars:
        print(f"📝 Remember to set these in Railway dashboard: {', '.join(missing_vars)}")
    
    return True

def main():
    """Main validation function."""
    print("🚂 Railway Deployment Validation")
    print("=" * 50)
    
    validation_results = []
    
    # 1. Configuration Files Validation
    print("\n📁 Configuration Files:")
    config_files = [
        ("railway.toml", "Railway configuration"),
        ("nixpacks.toml", "Nixpacks build configuration"), 
        ("Procfile", "Process definition"),
        ("start_railway.py", "Railway startup script"),
        ("src/railway_logger.py", "Railway logger"),
    ]
    
    config_ok = all(validate_file_exists(f, desc) for f, desc in config_files)
    validation_results.append(("Configuration Files", config_ok))
    
    # 2. Check that old AWS/Docker files are removed
    print("\n🗑️ Legacy File Cleanup:")
    legacy_files = [
        "Dockerfile",
        "docker-compose.yml", 
        "DOCKER_DEPLOYMENT_GUIDE.md",
        "src/aws_logger.py"
    ]
    
    legacy_clean = True
    for file_path in legacy_files:
        if os.path.exists(file_path):
            print(f"❌ Legacy file still exists: {file_path}")
            legacy_clean = False
        else:
            print(f"✅ Legacy file properly removed: {file_path}")
    
    validation_results.append(("Legacy File Cleanup", legacy_clean))
    
    # 3. Content Validation
    print("\n📝 Content Validation:")
    content_checks = [
        ("src/main.py", "railway_logger", "Main app uses Railway logger"),
        ("railway.toml", "nixpacks", "Railway config uses Nixpacks"),
        ("nixpacks.toml", "poetry install", "Nixpacks installs Poetry dependencies"),
    ]
    
    content_ok = all(validate_file_content(f, content, desc) for f, content, desc in content_checks)
    validation_results.append(("Content Validation", content_ok))
    
    # 4. Import Tests
    import_ok = validate_imports()
    validation_results.append(("Import Tests", import_ok))
    
    # 5. Poetry Setup
    poetry_ok = validate_poetry_setup()
    validation_results.append(("Poetry Setup", poetry_ok))
    
    # 6. Requirements Check
    req_ok = validate_requirements()
    validation_results.append(("Requirements Check", req_ok))
    
    # 7. Environment Variables
    env_ok = validate_environment_variables()
    validation_results.append(("Environment Variables", env_ok))
    
    # Final Summary
    print("\n🏁 Validation Summary:")
    print("=" * 50)
    
    all_passed = True
    for check_name, passed in validation_results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{check_name}: {status}")
        all_passed &= passed
    
    print("-" * 50)
    if all_passed:
        print("🎉 Railway deployment validation PASSED!")
        print("🚂 Ready for Railway deployment!")
        print("\n📋 Next Steps:")
        print("1. Commit and push to GitHub: git add . && git commit -m 'Railway deployment ready' && git push")
        print("2. Create Railway project from GitHub repo")
        print("3. Set environment variables in Railway dashboard")  
        print("4. Deploy and monitor logs")
        sys.exit(0)
    else:
        print("💥 Railway deployment validation FAILED!")
        print("🔧 Please fix the issues above before deploying.")
        sys.exit(1)

if __name__ == "__main__":
    main()