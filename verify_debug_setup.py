#!/usr/bin/env python
"""
Verification script to check that the VS Code debug setup is working correctly.
Run this before using the debugger to ensure everything is configured properly.
"""

import os
import sys
import subprocess
from pathlib import Path


def check_venv():
    """Check if we're using the correct virtual environment"""
    venv_path = Path(".venv/bin/python").resolve()
    current_python = Path(sys.executable).resolve()
    
    print("📍 Python Interpreter Check")
    print(f"   Expected: {venv_path}")
    print(f"   Current:  {current_python}")
    
    if current_python == venv_path:
        print("   ✅ Virtual environment is activated correctly\n")
        return True
    else:
        print("   ⚠️  Virtual environment may not be activated\n")
        return False


def check_pythonpath():
    """Check if PYTHONPATH includes src/"""
    pythonpath = os.environ.get("PYTHONPATH", "")
    
    print("📍 PYTHONPATH Check")
    print(f"   PYTHONPATH: {pythonpath}")
    
    src_path = str(Path("src").resolve())
    if "src" in pythonpath or src_path in pythonpath:
        print("   ✅ src/ is in PYTHONPATH\n")
        return True
    else:
        print("   ⚠️  src/ is not in PYTHONPATH\n")
        return False


def check_modules():
    """Check if required modules are installed"""
    print("📍 Required Modules Check")
    
    required_modules = [
        "streamlit",
        "supabase",
        "python-dotenv",
        "pytest",
        "pylint",
        "black",
    ]
    
    all_installed = True
    for module in required_modules:
        try:
            __import__(module)
            print(f"   ✅ {module}")
        except ImportError:
            print(f"   ❌ {module} (not installed)")
            all_installed = False
    
    print()
    return all_installed


def check_env_file():
    """Check if .env file exists"""
    print("📍 Environment File Check")
    
    env_path = Path(".env")
    if env_path.exists():
        print(f"   ✅ .env file exists")
        
        # Check for required vars
        with open(env_path) as f:
            content = f.read()
            if "SUPABASE_URL" in content:
                print(f"   ✅ SUPABASE_URL is set")
            else:
                print(f"   ⚠️  SUPABASE_URL not found in .env")
            
            if "SUPABASE_KEY" in content:
                print(f"   ✅ SUPABASE_KEY is set")
            else:
                print(f"   ⚠️  SUPABASE_KEY not found in .env")
    else:
        print(f"   ⚠️  .env file not found (optional but recommended)")
    
    print()


def check_vscode_config():
    """Check if VS Code config files exist"""
    print("📍 VS Code Configuration Check")
    
    vscode_files = [
        ".vscode/launch.json",
        ".vscode/settings.json",
        ".vscode/tasks.json",
    ]
    
    all_present = True
    for file in vscode_files:
        if Path(file).exists():
            print(f"   ✅ {file}")
        else:
            print(f"   ❌ {file} (missing)")
            all_present = False
    
    print()
    return all_present


def test_imports():
    """Test if key project modules can be imported"""
    print("📍 Project Modules Import Check")
    
    try:
        from politician_trading.config import WorkflowConfig
        print(f"   ✅ politician_trading.config")
    except ImportError as e:
        print(f"   ❌ politician_trading.config: {e}")
    
    try:
        from politician_trading.workflow import PoliticianTradingWorkflow
        print(f"   ✅ politician_trading.workflow")
    except ImportError as e:
        print(f"   ❌ politician_trading.workflow: {e}")
    
    try:
        from politician_trading.database import PoliticianTradingDB
        print(f"   ✅ politician_trading.database")
    except ImportError as e:
        print(f"   ❌ politician_trading.database: {e}")
    
    print()


def main():
    """Run all checks"""
    print("\n" + "="*60)
    print("VS Code Debug Setup Verification")
    print("="*60 + "\n")
    
    checks = [
        check_venv,
        check_pythonpath,
        check_modules,
        check_env_file,
        check_vscode_config,
        test_imports,
    ]
    
    results = []
    for check in checks:
        try:
            results.append(check())
        except Exception as e:
            print(f"❌ Error during check: {e}\n")
            results.append(False)
    
    # Summary
    print("="*60)
    if all(results):
        print("✅ All checks passed! You're ready to debug.")
    else:
        print("⚠️  Some checks failed. See above for details.")
    print("="*60 + "\n")
    
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
