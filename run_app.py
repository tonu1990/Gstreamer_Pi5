import sys, os
from pathlib import Path

# Ensure 'App_dev' is on sys.path when running from repo root
ROOT = Path(__file__).resolve().parent
APP_DIR = ROOT / "App_dev"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from app.main import main

if __name__ == "__main__":
    sys.exit(main())
