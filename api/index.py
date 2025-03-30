# api/index.py
import sys
import os
from pathlib import Path

# Add the project root to the Python path
root = Path(__file__).parent.parent
sys.path.insert(0, str(root))

# Print debugging information to Vercel logs
print(f"Python path: {sys.path}")
print(f"Current directory: {os.getcwd()}")
print(f"Directory contents: {os.listdir('.')}")

try:
    # Set Vercel environment flag
    os.environ["VERCEL"] = "1"

    # First, check if we can import the config
    from app.tvdb.config import settings, log_environment_info

    # Log environment info for debugging
    log_environment_info()

    # Import the FastAPI app from your main application
    from app.main import app

    print("Successfully imported app")

    # This is the handler Vercel will use
    handler = app

except Exception as e:
    print(f"Error importing app: {str(e)}")
    # Provide a fallback handler that returns the error
    from fastapi import FastAPI

    error_app = FastAPI()


    @error_app.get("/{path:path}")
    async def error_handler(path: str):
        return {
            "error": "Application failed to start",
            "details": str(e),
            "python_path": sys.path,
            "current_directory": os.getcwd(),
            "directory_contents": os.listdir('.'),
            "env_vars": list(os.environ.keys())
        }


    handler = error_app