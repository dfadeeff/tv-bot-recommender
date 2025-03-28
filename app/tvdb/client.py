"""TVDB API client implementation."""

import os
import time
from typing import Dict, List, Optional, Any

import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# TVDB API Configuration
TVDB_API_URL = "https://api4.thetvdb.com/v4"
TVDB_API_KEY = os.getenv("TVDB_API_KEY")
TVDB_PIN = os.getenv("TVDB_PIN")


class TVDBError(Exception):
    """Exception raised for TVDB API errors."""

    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"TVDB API Error ({status_code}): {message}")


class TVDBClient:
    """Client for interacting with the TVDB API."""

    def __init__(self):
        self.api_url = TVDB_API_URL
        self.api_key = TVDB_API_KEY
        self.pin = TVDB_PIN
        self.token = None
        self.token_expires = 0
        self.headers = {"Content-Type": "application/json"}

    def _ensure_token(self):
        """Ensure a valid token is available for API requests."""
        current_time = time.time()

        # If token is expired or not set, get a new one
        if not self.token or current_time >= self.token_expires:
            self._login()

    def _login(self):
        """Authenticate with the TVDB API and get an access token."""
        login_url = f"{self.api_url}/login"
        payload = {
            "apikey": self.api_key,
        }

        if self.pin:
            payload["pin"] = self.pin

        response = requests.post(login_url, json=payload)

        if response.status_code != 200:
            raise TVDBError(
                response.status_code,
                f"Authentication failed: {response.text}"
            )

        data = response.json()
        self.token = data["data"]["token"]
        # Token expires in 1 month, but we'll set it to expire in 29 days to be safe
        self.token_expires = time.time() + (29 * 24 * 60 * 60)
        self.headers["Authorization"] = f"Bearer {self.token}"

    def _make_request(
            self,
            method: str,
            endpoint: str,
            params: Optional[Dict] = None,
            data: Optional[Dict] = None
    ) -> Dict:
        """Make a request to the TVDB API."""
        self._ensure_token()

        url = f"{self.api_url}{endpoint}"

        try:
            response = requests.request(
                method,
                url,
                headers=self.headers,
                params=params,
                json=data
            )

            if response.status_code == 401:
                # Token might be expired, try to get a new one
                self.token = None
                self._ensure_token()

                # Retry the request
                response = requests.request(
                    method,
                    url,
                    headers=self.headers,
                    params=params,
                    json=data
                )

            if response.status_code != 200:
                raise TVDBError(
                    response.status_code,
                    f"API request failed: {response.text}"
                )

            return response.json()

        except requests.exceptions.RequestException as e:
            raise TVDBError(500, f"Request failed: {str(e)}")

    def search_series(
            self,
            query: str,
            limit: int = 5,
            year: Optional[int] = None,
            country: Optional[str] = None,
            network: Optional[str] = None,
            status: Optional[str] = None,
            genre: Optional[str] = None
    ) -> List[Dict]:
        """Search for TV series by name.

        Args:
            query: Search term
            limit: Maximum number of results
            year: Filter by year
            country: Filter by country of origin
            network: Filter by network
            status: Filter by series status (e.g., "Continuing", "Ended")
            genre: Filter by genre

        Returns:
            List of TV series matching the search criteria
        """
        # Use the general search endpoint with type=series
        params = {
            "q": query,
            "type": "series"
        }

        response = self._make_request("GET", "/search", params=params)

        # Filter and limit results
        results = response.get("data", [])

        # Apply additional filtering if needed
        if year or country or network or status or genre:
            filtered_results = []
            for series in results:
                if year and series.get("year") != year:
                    continue
                if country and country.lower() not in series.get("country", "").lower():
                    continue
                if network and series.get("network") and network.lower() not in series.get("network").lower():
                    continue
                if status and series.get("status") and status.lower() not in series.get("status").lower():
                    continue
                # Genre would need series details to filter, we'll skip here for simplicity
                filtered_results.append(series)
            results = filtered_results

        # Return limited results
        return results[:limit]

    def get_series_details(self, series_id: int) -> Dict:
        """Get detailed information about a TV series.

        Args:
            series_id: The ID of the TV series

        Returns:
            Details about the TV series
        """
        response = self._make_request("GET", f"/series/{series_id}/extended")
        return response.get("data", {})

    def get_series_cast(self, series_id: int) -> List[Dict]:
        """Get the cast of a TV series."""
        response = self._make_request("GET", f"/series/{series_id}/extended")
        return response.get("data", {}).get("characters", [])

    def get_similar_series(self, series_id: int) -> List[Dict]:
        """Get similar TV series recommendations based on genres."""
        series_details = self.get_series_details(series_id)

        # Get the genres of the series
        genres = [genre.get("name") for genre in series_details.get("genres", [])]

        if not genres:
            return []

        # Use the first genre to search for similar shows
        primary_genre = genres[0]
        search_results = self.search_series(primary_genre, limit=10)

        # Filter out the original series
        similar_series = [
            series for series in search_results
            if series.get("id") != series_id
        ]

        return similar_series[:5]  # Return up to 5 similar series

    def get_series_by_network(self, network: str, limit: int = 5) -> List[Dict]:
        """Get TV series by network."""
        # First, find the network ID
        networks = self._make_request("GET", "/networks").get("data", [])
        network_id = None

        for n in networks:
            if network.lower() in n.get("name", "").lower():
                network_id = n.get("id")
                break

        if not network_id:
            return []

        # Then search for series on that network
        params = {
            "network": network_id,
            "limit": limit
        }

        response = self._make_request("GET", "/series", params=params)
        return response.get("data", [])
