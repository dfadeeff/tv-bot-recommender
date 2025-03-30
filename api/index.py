# api/index.py
import sys
from pathlib import Path

# Add the project root to the Python path
root = Path(__file__).parent.parent
sys.path.insert(0, str(root))

# Import the FastAPI app from your main application
from app.main import app

# This is the handler Vercel will use
handler = app