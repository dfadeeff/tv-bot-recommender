from fastapi import FastAPI
from app.main import app as fastapi_app

# This is the handler that Vercel looks for
def handler(request):
    return fastapi_app(request)

# Vercel also looks for an "app" variable
app = fastapi_app