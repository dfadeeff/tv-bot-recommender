"""Test script for TVDB API."""

import os
import sys
import json
from datetime import datetime
from dotenv import load_dotenv
import requests

# Load environment variables from .env file
load_dotenv()

# TVDB API Configuration
TVDB_API_URL = "https://api4.thetvdb.com/v4"
TVDB_API_KEY = os.getenv("TVDB_API_KEY")
TVDB_PIN = os.getenv("TVDB_PIN")


def get_token():
    """Get an access token from the TVDB API."""
    login_url = f"{TVDB_API_URL}/login"

    # Print what we're using to authenticate
    print(f"API Key: {TVDB_API_KEY}")
    print(f"PIN: {TVDB_PIN if TVDB_PIN else 'Not provided'}")

    # Create the payload according to API docs
    payload = {
        "apikey": TVDB_API_KEY
    }

    # Add PIN only if it exists and is not empty
    if TVDB_PIN and TVDB_PIN.strip():
        payload["pin"] = TVDB_PIN

    print(f"Login payload: {json.dumps(payload)}")

    # Make the request
    try:
        response = requests.post(
            login_url,
            json=payload,
            headers={"Content-Type": "application/json"}
        )

        print(f"Login response status: {response.status_code}")
        print(f"Login response: {response.text}")

        if response.status_code != 200:
            print(f"Authentication failed: {response.text}")
            return None

        data = response.json()
        token = data["data"]["token"]
        print("Authentication successful!")
        return token
    except Exception as e:
        print(f"Exception during login: {str(e)}")
        return None


def search_series(token, query, limit=5):
    """Search for TV series by name."""
    search_url = f"{TVDB_API_URL}/search"  # Changed endpoint
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    params = {
        "q": query,
        "type": "series"  # Added type parameter
    }

    print(f"Search headers: {headers}")
    print(f"Search params: {params}")

    print(f"Searching for series matching '{query}'...")
    try:
        response = requests.get(search_url, headers=headers, params=params)

        print(f"Search response status: {response.status_code}")
        print(f"Search response: {response.text[:200]}...")  # Show first 200 chars to avoid too much output

        if response.status_code != 200:
            print(f"Search failed: {response.text}")
            return []

        data = response.json()
        results = data.get("data", [])
        # Limit results
        return results[:limit]
    except Exception as e:
        print(f"Exception during search: {str(e)}")
        return []


def main():
    """Main function."""
    print(f"Starting TVDB API test at {datetime.now()}")

    # Check if API key is available
    if not TVDB_API_KEY:
        print("Error: TVDB_API_KEY not found in .env file")
        sys.exit(1)

    # Get token
    token = get_token()
    if not token:
        print("Failed to get token. Exiting.")
        sys.exit(1)

    # Search for a series
    query = "Breaking Bad"
    results = search_series(token, query)

    if not results:
        print(f"No results found for '{query}'")
        sys.exit(1)

    # Print search results
    print(f"\nFound {len(results)} results for '{query}':")
    for i, series in enumerate(results, 1):
        print(f"{i}. {series.get('name')} (ID: {series.get('id')})")


if __name__ == "__main__":
    main()
