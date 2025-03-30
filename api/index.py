# api/index.py
import sys
import os
from pathlib import Path

# Add the project root to the Python path
root = Path(__file__).parent.parent
sys.path.insert(0, str(root))

# Set environment flag
os.environ["VERCEL"] = "1"

# Print debugging information
print(f"Python path: {sys.path}")
print(f"Current directory: {os.getcwd()}")
print(f"Directory contents: {os.listdir('.')}")

try:
    # Very simple import - just the app
    from app.main import app

    print("Successfully imported app")
    handler = app

except Exception as e:
    # For debugging
    from fastapi import FastAPI

    print(f"Error importing app: {str(e)}")
    error_app = FastAPI()


    @error_app.get("/{path:path}")
    async def error_handler(path: str):
        return {
            "error": f"Application failed to start: {str(e)}",
            "path": path
        }


    handler = error_app