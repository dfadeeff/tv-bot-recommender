"""Main FastAPI application for TV Series Recommender."""

import os
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi import Request

from app.tvdb.client import TVDBClient
from app.tvdb.models import ChatRequest, ChatResponse
from app.chatbot.bot import TVSeriesBot

# Create FastAPI app
app = FastAPI(
    title="TV Series Recommender",
    description="A chatbot that helps users discover TV series based on their preferences using the TVDB API.",
    version="0.2.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
try:
    app.mount("/static", StaticFiles(directory="app/static"), name="static")
except RuntimeError:
    # Directory might not exist in development
    pass

# Initialize Jinja2 templates
try:
    templates = Jinja2Templates(directory="app/templates")
except RuntimeError:
    # Directory might not exist in development
    templates = None

# Create TVDB client
tvdb_client = TVDBClient()
tv_series_bot = TVSeriesBot()


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Serve the HTML index page."""
    if templates:
        return templates.TemplateResponse("index.html", {"request": request})
    return HTMLResponse(content="<html><body><h1>TV Series Recommender API</h1></body></html>")


@app.get("/api/search/{query}")
async def search_series(query: str, limit: int = 5):
    """Search for TV series by name."""
    try:
        results = tvdb_client.search_series(query, limit=limit)
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/series/{series_id}")
async def get_series(series_id: str):
    """Get detailed information about a TV series."""
    try:
        # Extract numeric ID from the series ID string (e.g., "series-81189" -> 81189)
        numeric_id = None
        if series_id.startswith("series-"):
            numeric_id = int(series_id.replace("series-", ""))
        else:
            try:
                numeric_id = int(series_id)
            except ValueError:
                # If it's not a numeric ID, search for the series first
                results = tvdb_client.search_series(series_id, limit=1)
                if results:
                    series_id = results[0].get("id")
                    if series_id and series_id.startswith("series-"):
                        numeric_id = int(series_id.replace("series-", ""))

        if not numeric_id:
            raise HTTPException(status_code=404, detail="Series not found")

        details = tvdb_client.get_series_details(numeric_id)
        return {"details": details}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# @app.post("/api/chat", response_model=ChatResponse)
# async def chat(request: ChatRequest):
#     """Process a chat message."""
#     try:
#         # For now, just search for the message as a series name
#         results = tvdb_client.search_series(request.message, limit=3)
#
#         if results:
#             response_text = f"I found these TV series matching '{request.message}':\n\n"
#             for i, series in enumerate(results, 1):
#                 series_name = series.get("name", "Unknown")
#                 response_text += f"{i}. {series_name}\n"
#
#             # Get details for the first result
#             if results:
#                 series_id_str = results[0].get("id")
#                 series_name = results[0].get("name", "Unknown")
#
#                 # Extract numeric ID from the series ID string (e.g., "series-81189" -> 81189)
#                 numeric_id = None
#                 if series_id_str and series_id_str.startswith("series-"):
#                     numeric_id = int(series_id_str.replace("series-", ""))
#
#                 if numeric_id:
#                     details = tvdb_client.get_series_details(numeric_id)
#
#                     response_text += f"\nHere's more about '{series_name}':\n"
#
#                     overview = details.get("overview")
#                     if overview:
#                         response_text += f"Overview: {overview[:150]}...\n"
#
#                     genres = details.get("genres", [])
#                     genre_names = [genre.get("name") for genre in genres]
#                     if genre_names:
#                         response_text += f"Genres: {', '.join(genre_names)}\n"
#
#                     status = details.get("status")
#                     if status:
#                         response_text += f"Status: {status}\n"
#         else:
#             response_text = f"I couldn't find any TV series matching '{request.message}'. Try a different search term."
#
#         # For now, just use a fixed session ID
#         session_id = request.session_id or "default_session"
#
#         return ChatResponse(message=response_text, session_id=session_id)
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Process a chat message using the LLM-powered chatbot."""
    try:
        # Process the message through the chatbot
        response_text, session_id = tv_series_bot.process_query(
            request.message,
            session_id=request.session_id
        )

        return ChatResponse(message=response_text, session_id=session_id)
    except Exception as e:
        print(f"Error in chat endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/similar/{series_id}")
async def get_similar(series_id: str, limit: int = 5):
    """Get similar TV series recommendations."""
    try:
        # Extract numeric ID from the series ID string (e.g., "series-81189" -> 81189)
        numeric_id = None
        if series_id.startswith("series-"):
            numeric_id = int(series_id.replace("series-", ""))
        else:
            try:
                numeric_id = int(series_id)
            except ValueError:
                # If it's not a numeric ID, search for the series first
                results = tvdb_client.search_series(series_id, limit=1)
                if results:
                    series_id = results[0].get("id")
                    if series_id and series_id.startswith("series-"):
                        numeric_id = int(series_id.replace("series-", ""))

        if not numeric_id:
            raise HTTPException(status_code=404, detail="Series not found")

        similar = tvdb_client.get_similar_series(numeric_id)
        return {"similar": similar[:limit]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}
