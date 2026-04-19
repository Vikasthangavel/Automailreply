"""
Quick Setup Script - Run this to verify everything is ready!
"""

import sys
from pathlib import Path
import subprocess

def check_python_version():
    """Check Python version."""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("✗ Python 3.8+ required")
        return False
    print(f"✓ Python {version.major}.{version.minor} found")
    return True


def check_virtual_env():
    """Check if in virtual environment."""
    in_venv = sys.prefix != sys.base_prefix
    if not in_venv:
        print("⚠ Not in virtual environment")
        print("  Run: python -m venv venv && venv\\Scripts\\activate")
        return False
    print("✓ Virtual environment active")
    return True


def check_dependencies():
    """Check if required packages are installed."""
    required = ['pandas', 'openpyxl', 'rapidfuzz', 'dotenv']
    missing = []
    
    for package in required:
        try:
            __import__(package)
            print(f"✓ {package}")
        except ImportError:
            missing.append(package)
            print(f"✗ {package}")
    
    if missing:
        print(f"\n  Install: pip install -r requirements.txt")
        return False
    
    return True


def check_env_file():
    """Check if .env file exists."""
    if not Path(".env").exists():
        print("✗ .env file not found")
        print("  Run: copy .env.example .env")
        return False
    
    # Read .env and check for placeholders
    with open(".env") as f:
        content = f.read()
    
    if "your-email@gmail.com" in content or "your-app-password-here" in content:
        print("⚠ .env file contains placeholders")
        print("  Edit .env with your actual Gmail credentials")
        return False
    
    print("✓ .env file configured")
    return True


def check_excel_file():
    """Check if Excel file exists."""
    if not Path("data/KeywordandResponses.xlsx").exists():
        print("✗ Excel file not found")
        print("  Run: python create_sample_excel.py")
        return False
    
    print("✓ Excel file found")
    return True


def main():
    """Run all checks."""
    print("\n" + "="*60)
    print("Email Automation System - Setup Verification")
    print("="*60)
    
    checks = [
        ("Python Version", check_python_version),
        ("Virtual Environment", check_virtual_env),
        ("Dependencies", check_dependencies),
        ("Environment File (.env)", check_env_file),
        ("Excel Knowledge Base", check_excel_file),
    ]
    
    results = {}
    for name, check_func in checks:
        print(f"\n{name}:")
        try:
            results[name] = check_func()
        except Exception as e:
            print(f"✗ Error: {e}")
            results[name] = False
    
    # Summary
    print("\n" + "="*60)
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    if passed == total:
        print(f"✓ All checks passed! ({passed}/{total})")
        print("\nYou're ready to run: python main.py")
        return 0
    else:
        print(f"✗ {total - passed} check(s) failed ({passed}/{total})")
        print("\nFix the issues above and run this script again")
        return 1


if __name__ == "__main__":
    sys.exit(main())
