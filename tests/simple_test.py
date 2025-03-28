"""Minimal TVDB API test."""

import os
import json
import requests
from dotenv import load_dotenv

# Load API key from .env
load_dotenv()
API_KEY = os.getenv("TVDB_API_KEY")


# Try to authenticate
def test_auth():
    print(f"Testing TVDB API authentication with key: {API_KEY}")
    url = "https://api4.thetvdb.com/v4/login"
    payload = {"apikey": API_KEY}

    try:
        response = requests.post(url, json=payload)
        print(f"Status code: {response.status_code}")
        print(f"Response: {response.text[:200]}...")  # Show first 200 chars

        if response.status_code == 200:
            print("Authentication successful!")
            data = response.json()
            token = data["data"]["token"]
            return token
        else:
            print("Authentication failed.")
            return None
    except Exception as e:
        print(f"Exception: {str(e)}")
        return None


# Try a simple search if auth is successful
def test_search(token):
    if not token:
        return

    print("\nTesting search functionality")
    url = "https://api4.thetvdb.com/v4/search"  # Using general search endpoint
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    params = {
        "q": "Breaking Bad"
    }

    try:
        print(f"Making request to {url} with params {params}")
        response = requests.get(url, headers=headers, params=params)
        print(f"Status code: {response.status_code}")
        print(f"Response: {response.text[:300]}...")  # First 300 chars

        if response.status_code == 200:
            data = response.json()
            results = data.get("data", [])
            print(f"Found {len(results)} results")
            for i, item in enumerate(results[:5], 1):
                if "name" in item:
                    print(f"{i}. {item.get('name')}")
    except Exception as e:
        print(f"Exception: {str(e)}")


# Try another search endpoint
def test_search_by_type(token):
    if not token:
        return

    print("\nTesting search with type parameter")
    url = "https://api4.thetvdb.com/v4/search"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    params = {
        "q": "Breaking Bad",
        "type": "series"  # Specify series type
    }

    try:
        print(f"Making request to {url} with params {params}")
        response = requests.get(url, headers=headers, params=params)
        print(f"Status code: {response.status_code}")
        print(f"Response: {response.text[:300]}...")  # First 300 chars

        if response.status_code == 200:
            data = response.json()
            results = data.get("data", [])
            print(f"Found {len(results)} results")
            for i, item in enumerate(results[:5], 1):
                if "name" in item:
                    print(f"{i}. {item.get('name')}")
    except Exception as e:
        print(f"Exception: {str(e)}")


# Run tests
if __name__ == "__main__":
    token = test_auth()
    test_search(token)
    test_search_by_type(token)