"""TVDB API client implementation."""

import os
import time
from typing import Dict, List, Optional, Any
from app.tvdb.models import Episode, Series, SearchResult, SeriesBase

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
        """Search for TV series by name."""
        # Use the general search endpoint with type=series
        params = {
            "q": query,
            "type": "series"
        }

        response = self._make_request("GET", "/search", params=params)
        results = response.get("data", [])

        # Print raw response data for debugging
        print(f"Raw search results for '{query}': {len(results)} items")

        # Validate and transform results using your SeriesBase model
        validated_results = []
        for result in results:
            try:
                # Pre-process any known problematic fields
                if "status" in result and isinstance(result["status"], str):
                    # Create a proper Status object
                    result["status"] = {"id": 0, "name": result["status"]}

                # Handle ID format conversion if needed
                if "id" in result and isinstance(result["id"], str) and result["id"].startswith("series-"):
                    try:
                        result["id"] = int(result["id"].replace("series-", ""))
                    except ValueError:
                        pass

                # Add minimum required fields if missing
                if "slug" not in result:
                    result["slug"] = result.get("name", "").lower().replace(" ", "-")

                # Validate with model, but use exclude_unset to handle missing fields
                series = SeriesBase.parse_obj(result)
                validated_results.append(series.dict(exclude_unset=True))
            except Exception as e:
                print(f"Error validating series data for item {result.get('name', 'unknown')}: {e}")
                # Add the original data as fallback
                validated_results.append(result)

        # Apply additional filtering if needed
        if year or country or network or status or genre:
            filtered_results = []
            for series in validated_results:
                if year and series.get("year") != year:
                    continue
                if country and country.lower() not in series.get("country", "").lower():
                    continue
                if network and series.get("network") and network.lower() not in series.get("network").lower():
                    continue
                if status and series.get("status"):
                    # Handle status which may now be an object
                    if isinstance(series.get("status"), dict):
                        if status.lower() not in series["status"].get("name", "").lower():
                            continue
                    elif isinstance(series.get("status"), str):
                        if status.lower() not in series["status"].lower():
                            continue
                # Genre would need series details to filter, we'll skip here for simplicity
                filtered_results.append(series)
            validated_results = filtered_results

        # Return limited results
        return validated_results[:limit]

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
        """Get episodes of a TV series by season number."""
        try:
            # Existing code to fetch episodes
            season_type = "default"
            endpoint = f"/series/{series_id}/episodes/{season_type}"
            print(f"Fetching episodes from endpoint: {endpoint}")

            response = self._make_request("GET", endpoint)
            all_episodes_data = response.get("data", [])

            if not all_episodes_data:
                print(f"No episodes found for series {series_id}")
                return []

            print(f"Found {len(all_episodes_data)} total episodes for series {series_id}")

            # Convert raw dictionaries to Episode models
            validated_episodes = []
            for episode_data in all_episodes_data:
                try:
                    # Add series_id if it's missing in the API response
                    if "series_id" not in episode_data and "seriesId" not in episode_data:
                        episode_data["seriesId"] = series_id

                    # Ensure episode has a name (required by your model)
                    if "name" not in episode_data or not episode_data["name"]:
                        episode_data["name"] = "Untitled Episode"

                    # Create Episode model and validate the data with better error handling
                    episode = Episode.parse_obj(episode_data)
                    validated_episodes.append(episode.dict())
                except Exception as e:
                    print(f"Error validating episode: {e}")
                    # For episodes, add a minimally processed version instead of skipping
                    # This ensures we return something even if validation fails
                    basic_episode = {
                        "id": episode_data.get("id", 0),
                        "seriesId": series_id,
                        "name": episode_data.get("name", "Untitled"),
                        "number": episode_data.get("number", episode_data.get("episodeNumber")),
                        "seasonNumber": episode_data.get("seasonNumber", episode_data.get("season")),
                        "overview": episode_data.get("overview", ""),
                        "aired": episode_data.get("aired", episode_data.get("firstAired"))
                    }
                    validated_episodes.append(basic_episode)

            # Filter by season if needed
            if season_number is not None:
                filtered_episodes = []
                for episode in validated_episodes:
                    # Check season number with different possible field names
                    ep_season = episode.get("season_number", episode.get("seasonNumber"))
                    if ep_season == season_number or str(ep_season) == str(season_number):
                        filtered_episodes.append(episode)

                print(f"Filtered to {len(filtered_episodes)} episodes for season {season_number}")
                return filtered_episodes

            # Return all episodes
            return validated_episodes

        except Exception as e:
            print(f"Error in get_series_episodes_by_season: {e}")
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

    def advanced_search(
            self,
            query: Optional[str] = None,
            type: Optional[str] = None,
            year: Optional[int] = None,
            country: Optional[str] = None,
            company: Optional[str] = None,
            language: Optional[str] = None,
            director: Optional[str] = None,
            primary_type: Optional[str] = None,
            network: Optional[str] = None,
            remote_id: Optional[str] = None,
            offset: int = 0,
            limit: int = 5
    ) -> List[Dict]:
        """Advanced search for TVDB content with multiple filter options.

        Args:
            query: The search query string (also accepts 'q' as alias)
            type: Type of content to search (series, movie, person, company)
            year: Filter by year (primarily for series/movies)
            country: Filter by country code (3-letter code)
            company: Filter by company name (production company, studio, etc.)
            language: Filter by language code (3-letter code)
            director: Filter by director name (primarily for movies)
            primary_type: Filter by company type
            network: Filter by TV network name
            remote_id: Search by IMDB or EIDR ID
            offset: Result offset for pagination
            limit: Maximum number of results to return

        Returns:
            List of search results matching the criteria
        """
        # Build search parameters
        params = {}

        # Add query parameter (handles both 'query' and 'q')
        if query:
            params["query"] = query

        # Add filter parameters if provided
        if type:
            params["type"] = type
        if year:
            params["year"] = year
        if country:
            params["country"] = country
        if company:
            params["company"] = company
        if language:
            params["language"] = language
        if director:
            params["director"] = director
        if primary_type:
            params["primaryType"] = primary_type
        if network:
            params["network"] = network
        if remote_id:
            params["remote_id"] = remote_id

        # Add pagination parameters
        params["offset"] = offset
        params["limit"] = limit

        # Make the request
        print(f"Performing advanced search with parameters: {params}")
        try:
            response = self._make_request("GET", "/search", params=params)
            results = response.get("data", [])
            print(f"Found {len(results)} results")
            return results
        except TVDBError as e:
            print(f"Search error: {e}")
            return []

    def search_movies(
            self,
            query: Optional[str] = None,
            year: Optional[int] = None,
            director: Optional[str] = None,
            country: Optional[str] = None,
            language: Optional[str] = None,
            limit: int = 5
    ) -> List[Dict]:
        """Search for movies with specific filters.

        Args:
            query: Movie title or keywords
            year: Release year
            director: Director name
            country: Country of origin (3-letter code)
            language: Primary language (3-letter code)
            limit: Maximum number of results

        Returns:
            List of movies matching the criteria
        """
        return self.advanced_search(
            query=query,
            type="movie",
            year=year,
            director=director,
            country=country,
            language=language,
            limit=limit
        )

    def search_people(
            self,
            query: str,
            limit: int = 5
    ) -> List[Dict]:
        """Search for people (actors, directors, etc.).

        Args:
            query: Person name
            limit: Maximum number of results

        Returns:
            List of people matching the criteria
        """
        return self.advanced_search(
            query=query,
            type="person",
            limit=limit
        )

    def search_companies(
            self,
            query: Optional[str] = None,
            primary_type: Optional[str] = None,
            country: Optional[str] = None,
            limit: int = 5
    ) -> List[Dict]:
        """Search for companies.

        Args:
            query: Company name
            primary_type: Type of company (e.g., "Production Company")
            country: Country code (3-letter)
            limit: Maximum number of results

        Returns:
            List of companies matching the criteria
        """
        return self.advanced_search(
            query=query,
            type="company",
            primary_type=primary_type,
            country=country,
            limit=limit
        )

    def get_series_awards(self, series_id: int) -> List[Dict]:
        """Get awards for a TV series.

        Args:
            series_id: The ID of the TV series

        Returns:
            List of awards for the series
        """
        try:
            print(f"Fetching awards for series {series_id}")

            # Method 1: Try to get awards from extended series info
            extended_info = self.get_series_details(series_id)
            awards = extended_info.get("awards", [])

            if awards:
                print(f"Found {len(awards)} awards in extended series info")
                return awards

            # Method 2: Try the direct series awards endpoint
            print("No awards in extended info, trying direct awards endpoint")
            endpoint = f"/series/{series_id}/awards"
            response = self._make_request("GET", endpoint)
            awards = response.get("data", [])

            if awards:
                print(f"Found {len(awards)} awards with direct endpoint")
                return awards

            # Method 3: Try searching all awards for this series
            print("No awards found with direct endpoint, trying awards search")
            all_awards = self._make_request("GET", "/awards").get("data", [])

            # Look for awards related to this series
            series_awards = []
            for award in all_awards:
                # Check categories for this series
                categories = award.get("categories", [])
                for category in categories:
                    records = category.get("records", [])
                    for record in records:
                        if record.get("seriesId") == series_id:
                            series_awards.append({
                                "award_name": award.get("name"),
                                "category": category.get("name"),
                                "year": record.get("year"),
                                "nominee": record.get("nominee"),
                                "won": record.get("isWinner", False)
                            })

            print(f"Found {len(series_awards)} awards through search")
            return series_awards

        except TVDBError as e:
            print(f"TVDB API Error getting awards: {e}")
            return []
        except Exception as e:
            print(f"Unexpected error getting awards: {str(e)}")
            return []

    def get_movie_awards(self, movie_id: int) -> List[Dict]:
        """Get awards for a movie.

        Args:
            movie_id: The ID of the movie

        Returns:
            List of awards for the movie
        """
        try:
            print(f"Fetching awards for movie {movie_id}")

            # Method 1: Try to get awards from extended movie info
            extended_info = self._make_request("GET", f"/movies/{movie_id}/extended").get("data", {})
            awards = extended_info.get("awards", [])

            if awards:
                print(f"Found {len(awards)} awards in extended movie info")
                return awards

            # Method 2: Try the direct movie awards endpoint
            print("No awards in extended info, trying direct awards endpoint")
            endpoint = f"/movies/{movie_id}/awards"
            response = self._make_request("GET", endpoint)
            awards = response.get("data", [])

            if awards:
                print(f"Found {len(awards)} awards with direct endpoint")
                return awards

            # Method 3: Try searching all awards for this movie
            print("No awards found with direct endpoint, trying awards search")
            all_awards = self._make_request("GET", "/awards").get("data", [])

            # Look for awards related to this movie
            movie_awards = []
            for award in all_awards:
                # Check categories for this movie
                categories = award.get("categories", [])
                for category in categories:
                    records = category.get("records", [])
                    for record in records:
                        if record.get("movieId") == movie_id:
                            movie_awards.append({
                                "award_name": award.get("name"),
                                "category": category.get("name"),
                                "year": record.get("year"),
                                "nominee": record.get("nominee"),
                                "won": record.get("isWinner", False)
                            })

            print(f"Found {len(movie_awards)} awards through search")
            return movie_awards

        except TVDBError as e:
            print(f"TVDB API Error getting movie awards: {e}")
            return []
        except Exception as e:
            print(f"Unexpected error getting movie awards: {str(e)}")
            return []

    def get_people_awards(self, person_id: int) -> List[Dict]:
        """Get awards for a person (actor, director, etc.).

        Args:
            person_id: The ID of the person

        Returns:
            List of awards for the person
        """
        try:
            print(f"Fetching awards for person {person_id}")

            # Method 1: Try the direct person awards endpoint
            endpoint = f"/people/{person_id}/awards"
            response = self._make_request("GET", endpoint)
            awards = response.get("data", [])

            if awards:
                print(f"Found {len(awards)} awards with direct endpoint")
                return awards

            # Method 2: Try searching all awards for this person
            print("No awards found with direct endpoint, trying awards search")
            all_awards = self._make_request("GET", "/awards").get("data", [])

            # Look for awards related to this person
            person_awards = []
            for award in all_awards:
                # Check categories for this person
                categories = award.get("categories", [])
                for category in categories:
                    records = category.get("records", [])
                    for record in records:
                        if record.get("personId") == person_id:
                            person_awards.append({
                                "award_name": award.get("name"),
                                "category": category.get("name"),
                                "year": record.get("year"),
                                "nominee": record.get("nominee"),
                                "won": record.get("isWinner", False)
                            })

            print(f"Found {len(person_awards)} awards through search")
            return person_awards

        except TVDBError as e:
            print(f"TVDB API Error getting person awards: {e}")
            return []
        except Exception as e:
            print(f"Unexpected error getting person awards: {str(e)}")
            return []

    def get_award_by_id(self, award_id: int) -> Dict:
        """Get detailed information about an award by ID.

        Args:
            award_id: The ID of the award

        Returns:
            Award details
        """
        try:
            response = self._make_request("GET", f"/awards/{award_id}")
            return response.get("data", {})
        except Exception as e:
            print(f"Error getting award details: {e}")
            return {}

    def get_award_category(self, category_id: int) -> Dict:
        """Get detailed information about an award category.

        Args:
            category_id: The ID of the award category

        Returns:
            Award category details
        """
        try:
            response = self._make_request("GET", f"/awards/categories/{category_id}")
            return response.get("data", {})
        except Exception as e:
            print(f"Error getting award category details: {e}")
            return {}

    def get_award_extended(self, award_id: int) -> Dict:
        """Get extended information about an award by ID.

        Args:
            award_id: The ID of the award

        Returns:
            Extended award details including categories
        """
        try:
            response = self._make_request("GET", f"/awards/{award_id}/extended")
            return response.get("data", {})
        except Exception as e:
            print(f"Error getting extended award details: {e}")
            return {}
