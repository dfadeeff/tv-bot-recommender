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

    # Add these methods to your TVDBClient class in app/tvdb/client.py

    def get_series_episodes_by_season(self, series_id: int, season_number: Optional[int] = None) -> List[Dict]:
        """Get episodes of a TV series by season number.

        Args:
            series_id: The ID of the TV series
            season_number: Optional season number to filter by

        Returns:
            List of episodes matching the criteria
        """
        try:
            # According to API docs, the correct endpoint is /series/{id}/episodes/{season-type}
            # Valid season types from API docs typically include "default" or "official"
            season_type = "default"

            # First, get all episodes using the proper endpoint format
            endpoint = f"/series/{series_id}/episodes/{season_type}"
            print(f"Fetching episodes from endpoint: {endpoint}")

            response = self._make_request("GET", endpoint)
            all_episodes = response.get("data", [])

            if not all_episodes:
                print(f"No episodes found for series {series_id}")
                return []

            print(f"Found {len(all_episodes)} total episodes for series {series_id}")

            # If season number is specified, filter the results
            if season_number is not None:
                filtered_episodes = []
                for episode in all_episodes:
                    # Check all possible season number field names
                    season_num = episode.get("seasonNumber")
                    if season_num is None:
                        season_num = episode.get("season")

                    # Handle both integer and string comparisons
                    if season_num == season_number or str(season_num) == str(season_number):
                        filtered_episodes.append(episode)

                print(f"Filtered to {len(filtered_episodes)} episodes for season {season_number}")
                return filtered_episodes

            # Return all episodes if no season is specified
            return all_episodes

        except TVDBError as e:
            print(f"TVDB API Error: {e}")
            # Try fallback with /episodes/filter endpoint
            try:
                print(f"Trying fallback method with /episodes/filter")
                params = {"seriesId": series_id}
                if season_number is not None:
                    params["seasonNumber"] = season_number

                response = self._make_request("GET", "/episodes/filter", params=params)
                episodes = response.get("data", [])
                print(f"Fallback found {len(episodes)} episodes")
                return episodes
            except Exception as fallback_error:
                print(f"Fallback also failed: {fallback_error}")
                return []
        except Exception as e:
            print(f"Unexpected error getting episodes: {str(e)}")
            return []

    def get_series_next_aired(self, series_id: int) -> Dict:
        """Get information about the next episode to air.

        Args:
            series_id: The ID of the TV series

        Returns:
            Next aired episode information
        """
        response = self._make_request("GET", f"/series/{series_id}/nextAired")
        return response.get("data", {})

    def get_series_artworks(self, series_id: int) -> List[Dict]:
        """Get artworks for a TV series.

        Args:
            series_id: The ID of the TV series

        Returns:
            List of artwork items
        """
        response = self._make_request("GET", f"/series/{series_id}/artworks")
        return response.get("data", [])

    def get_series_by_slug(self, slug: str) -> Dict:
        """Get a TV series by its slug.

        Args:
            slug: Series slug

        Returns:
            Series details
        """
        response = self._make_request("GET", f"/series/slug/{slug}")
        return response.get("data", {})

    def get_season_details(self, season_id: int) -> Dict:
        """Get detailed information about a season.

        Args:
            season_id: The ID of the season

        Returns:
            Season details
        """
        response = self._make_request("GET", f"/seasons/{season_id}/extended")
        return response.get("data", {})

    def get_character_details(self, character_id: int) -> Dict:
        """Get detailed information about a character.

        Args:
            character_id: The ID of the character

        Returns:
            Character details
        """
        response = self._make_request("GET", f"/characters/{character_id}")
        return response.get("data", {})

    def get_series_filter(self, filters: Dict[str, Any]) -> List[Dict]:
        """Search for series using advanced filters.

        Args:
            filters: Dictionary of filter parameters

        Returns:
            List of TV series matching the filters
        """
        response = self._make_request("GET", "/series/filter", params=filters)
        return response.get("data", [])

    def debug_breaking_bad_episodes(self):
        """Debug method specifically for Breaking Bad episodes.
        Tries different approaches and prints detailed information.
        """
        import json

        try:
            # Step 1: Find Breaking Bad series ID
            print("Step 1: Searching for Breaking Bad")
            search_results = self.search_series("Breaking Bad", limit=1)

            if not search_results:
                print("Could not find Breaking Bad in search results")
                return

            # Extract the series ID
            series = search_results[0]
            print(f"Found Breaking Bad: {json.dumps(series, indent=2)}")

            series_id_str = series.get("id")
            print(f"Raw series ID: {series_id_str} (type: {type(series_id_str).__name__})")

            # Handle different ID formats
            series_id = None
            if isinstance(series_id_str, int):
                series_id = series_id_str
            elif isinstance(series_id_str, str):
                if series_id_str.startswith("series-"):
                    try:
                        series_id = int(series_id_str.replace("series-", ""))
                    except ValueError:
                        print(f"Could not parse series ID from {series_id_str}")
                        return
                else:
                    try:
                        series_id = int(series_id_str)
                    except ValueError:
                        print(f"Could not parse series ID from {series_id_str}")
                        return

            print(f"Parsed series ID: {series_id}")

            # Step 2: Try to get seasons
            print("\nStep 2: Getting seasons information")
            try:
                seasons_response = self._make_request("GET", f"/series/{series_id}/seasons")
                seasons = seasons_response.get("data", [])
                print(f"Found {len(seasons)} seasons")

                # Print first few seasons
                for i, season in enumerate(seasons[:3]):
                    print(f"Season {i + 1}: {json.dumps(season, indent=2)}")

            except Exception as e:
                print(f"Error getting seasons: {e}")

            # Step 3: Try multiple endpoints for season 3
            season_number = 3
            print(f"\nStep 3: Trying to get episodes for season {season_number}")

            # Approach 1: Direct episodes endpoint
            print("\nApproach 1: Using /series/{id}/episodes/default")
            try:
                response = self._make_request("GET", f"/series/{series_id}/episodes/default")
                all_episodes = response.get("data", [])
                print(f"Found {len(all_episodes)} total episodes")

                # Check first episode to understand structure
                if all_episodes:
                    print(f"Sample episode structure: {json.dumps(all_episodes[0], indent=2)}")

                    # Try to find season 3 episodes
                    season3 = [ep for ep in all_episodes
                               if (ep.get("seasonNumber") == season_number or
                                   ep.get("season") == season_number or
                                   str(ep.get("seasonNumber")) == str(season_number) or
                                   str(ep.get("season")) == str(season_number))]
                    print(f"Found {len(season3)} episodes for season {season_number}")

            except Exception as e:
                print(f"Approach 1 failed: {e}")

            # Approach 2: Filter endpoint
            print("\nApproach 2: Using /episodes/filter")
            try:
                params = {"seriesId": series_id, "seasonNumber": season_number}
                response = self._make_request("GET", "/episodes/filter", params=params)
                episodes = response.get("data", [])
                print(f"Found {len(episodes)} episodes with filter")

            except Exception as e:
                print(f"Approach 2 failed: {e}")

            # Approach 3: Get season ID first
            print("\nApproach 3: Finding season ID then getting episodes")
            try:
                # Find season 3
                season_id = None
                for season in seasons:
                    if (season.get("number") == season_number or
                            str(season.get("number")) == str(season_number)):
                        season_id = season.get("id")
                        break

                if season_id:
                    print(f"Found season ID: {season_id} for season {season_number}")
                    episodes_response = self._make_request("GET", f"/seasons/{season_id}/episodes")
                    episodes = episodes_response.get("data", [])
                    print(f"Found {len(episodes)} episodes using season ID")
                else:
                    print(f"Could not find season {season_number} ID")

            except Exception as e:
                print(f"Approach 3 failed: {e}")

            # Approach 4: Extended series info
            print("\nApproach 4: Using /series/{id}/extended")
            try:
                response = self._make_request("GET", f"/series/{series_id}/extended")
                extended_data = response.get("data", {})

                # Check if episodes are included
                episodes = extended_data.get("episodes", [])
                print(f"Extended data has {len(episodes)} episodes")

                if episodes:
                    season3 = [ep for ep in episodes if ep.get("seasonNumber") == season_number]
                    print(f"Found {len(season3)} episodes for season {season_number}")

            except Exception as e:
                print(f"Approach 4 failed: {e}")

        except Exception as e:
            print(f"Debug method failed with error: {e}")
            import traceback
            traceback.print_exc()
