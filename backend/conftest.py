# backend/conftest.py
# Adds the backend directory to sys.path so that all test imports resolve
# correctly when running:  pytest backend/tests
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
