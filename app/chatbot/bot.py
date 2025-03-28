"""Main chatbot implementation."""

from typing import Dict, List, Any, Optional, Tuple

from app.tvdb.client import TVDBClient
from app.chatbot.llm_service import LLMService
from app.chatbot.memory import ConversationMemory
from app.tvdb.models import UserQuery


class TVSeriesBot:
    """Main chatbot class for TV series recommendations."""

    def __init__(self):
        """Initialize the TV series bot."""
        self.tvdb_client = TVDBClient()
        self.llm_service = LLMService()
        self.memory = ConversationMemory()

    def process_query(self, query_text: str, session_id: Optional[str] = None) -> Tuple[str, str]:
        """Process a user query and generate a response.

        Args:
            query_text: User's query text
            session_id: Optional session ID for conversation context

        Returns:
            Tuple of (response text, session ID)
        """
        # Get or create session
        session_id = self.memory.get_or_create_session(session_id)

        # Get the current conversation context
        context = self.memory.get_context(session_id)

        # Parse the user's intent using LLM
        try:
            query = self.llm_service.parse_user_intent(query_text, context)

            # Add the query to memory
            self.memory.add_query(session_id, query)

            # Handle the intent
            results = self._handle_intent(query)

            # Update the series context if applicable
            if results and isinstance(results, list) and len(results) > 0:
                # Try to extract series IDs, handling different ID formats
                series_ids = []
                for item in results:
                    if isinstance(item, dict) and 'id' in item:
                        id_str = item['id']
                        # Handle "series-12345" format
                        if isinstance(id_str, str) and id_str.startswith("series-"):
                            try:
                                numeric_id = int(id_str.replace("series-", ""))
                                series_ids.append(numeric_id)
                            except ValueError:
                                pass
                        # Handle numeric IDs
                        elif isinstance(id_str, int):
                            series_ids.append(id_str)

                if series_ids:
                    self.memory.set_last_series_context(session_id, series_ids)

            # Generate a response
            response = self.llm_service.generate_response(query, results, context)
            return response, session_id

        except Exception as e:
            error_msg = f"Sorry, I encountered an error: {str(e)}"
            print(f"Error processing query: {str(e)}")
            return error_msg, session_id

    def _handle_intent(self, query: UserQuery) -> Any:
        """Handle the user's intent and perform the appropriate action.

        Args:
            query: Parsed user query

        Returns:
            Results from the TVDB API
        """
        intent = query.intent
        params = query.parameters

        # Default limit for results
        limit = 10

        if intent == "search_series":
            # Extract search parameters
            series_name = params.get("series_name", "")
            genre = params.get("genre")
            year = params.get("year")
            country = params.get("country")
            network = params.get("network")
            status = params.get("status")

            # If no series name specified but genre is, search by genre
            if not series_name and genre:
                return self.tvdb_client.search_series(
                    genre, limit=limit, year=year, country=country,
                    network=network, status=status
                )

            # Otherwise, search by series name
            return self.tvdb_client.search_series(
                series_name, limit=limit, year=year, country=country,
                network=network, status=status, genre=genre
            )

        elif intent == "get_series_details":
            series_name = params.get("series_name", "")

            # Search for the series
            results = self.tvdb_client.search_series(series_name, limit=1)

            if not results:
                return {"error": f"Could not find series '{series_name}'"}

            # Get the details for the first result
            series_id_str = results[0].get("id")

            # Extract numeric ID from string format (e.g., "series-12345")
            if series_id_str and isinstance(series_id_str, str) and series_id_str.startswith("series-"):
                try:
                    series_id = int(series_id_str.replace("series-", ""))
                    return self.tvdb_client.get_series_details(series_id)
                except ValueError:
                    return {"error": f"Invalid series ID format: {series_id_str}"}
            elif series_id_str and isinstance(series_id_str, int):
                return self.tvdb_client.get_series_details(series_id_str)
            else:
                return {"error": f"Could not find valid ID for series '{series_name}'"}

        elif intent == "get_similar_series":
            series_name = params.get("series_name", "")

            # Get the current conversation context
            context = self.memory.get_context("default_session")
            last_series = context.last_series_context

            if series_name:
                # Search for the series
                results = self.tvdb_client.search_series(series_name, limit=1)

                if not results:
                    return {"error": f"Could not find series '{series_name}'"}

                # Get the series ID
                series_id_str = results[0].get("id")

                # Extract numeric ID
                if series_id_str and isinstance(series_id_str, str) and series_id_str.startswith("series-"):
                    try:
                        series_id = int(series_id_str.replace("series-", ""))
                        return self.tvdb_client.get_similar_series(series_id)
                    except ValueError:
                        return {"error": f"Invalid series ID format: {series_id_str}"}
                elif series_id_str and isinstance(series_id_str, int):
                    return self.tvdb_client.get_similar_series(series_id_str)
                else:
                    return {"error": f"Could not find valid ID for series '{series_name}'"}

            elif last_series and len(last_series) > 0:
                # Use the first series from the last context
                return self.tvdb_client.get_similar_series(last_series[0])

            else:
                return {"error": "Please specify a TV series to find similar shows"}

        elif intent == "get_actor_filmography":
            actor_name = params.get("actor_name", "")

            if not actor_name:
                return {"error": "Please specify an actor name"}

            return self.tvdb_client.get_actors_filmography(actor_name)

        elif intent == "get_series_by_network":
            network = params.get("network", "")

            if not network:
                return {"error": "Please specify a network"}

            return self.tvdb_client.get_series_by_network(network, limit=limit)

        elif intent == "get_upcoming_series":
            genre = params.get("genre")
            return self.tvdb_client.get_upcoming_series(genre=genre)

        elif intent == "update_preferences":
            # Extract preferences from parameters
            genres = params.get("genres", []) if isinstance(params.get("genres"), list) else [
                params.get("genres")] if params.get("genres") else []
            actors = params.get("actors", []) if isinstance(params.get("actors"), list) else [
                params.get("actors")] if params.get("actors") else []
            networks = params.get("networks", []) if isinstance(params.get("networks"), list) else [
                params.get("networks")] if params.get("networks") else []

            # Update preferences
            self.memory.update_preferences(
                "default_session",
                genres=genres,
                actors=actors,
                networks=networks
            )

            # Return current preferences
            return {"preferences": self.memory.get_context("default_session").user_preferences.dict()}

        elif intent == "help":
            # Return help information
            return {
                "help": {
                    "description": "I can help you discover TV series based on your preferences.",
                    "examples": [
                        "I like sci-fi shows like Star Trek. What should I watch next?",
                        "Who stars in Stranger Things?",
                        "What are some upcoming fantasy series?",
                        "Tell me about shows on HBO.",
                        "What else has the cast of Breaking Bad been in?"
                    ]
                }
            }

        # Updated portion of _handle_intent method for episode retrieval
        elif intent == "get_series_episodes":
            series_name = params.get("series_name", "")
            season = params.get("season")

            # Debug info
            print(f"Getting episodes for '{series_name}', season {season}")

            # Ensure we have a series name
            if not series_name:
                return {"error": "Please specify a TV series name"}

            # Convert season to integer if it's a string number
            if season and isinstance(season, str) and season.isdigit():
                season = int(season)

            # Search for the series
            results = self.tvdb_client.search_series(series_name, limit=1)

            if not results:
                return {"error": f"Could not find series '{series_name}'"}

            # Get full information about the found series
            found_series = results[0]
            print(f"Found series: {found_series.get('name')} with ID {found_series.get('id')}")

            # Get the details for the first result
            series_id_str = found_series.get("id")
            series_id = None

            # Extract numeric ID from different possible formats
            if isinstance(series_id_str, int):
                series_id = series_id_str
            elif isinstance(series_id_str, str):
                if series_id_str.startswith("series-"):
                    try:
                        series_id = int(series_id_str.replace("series-", ""))
                    except ValueError:
                        return {"error": f"Invalid series ID format: {series_id_str}"}
                else:
                    try:
                        series_id = int(series_id_str)
                    except ValueError:
                        return {"error": f"Invalid series ID format: {series_id_str}"}
            else:
                return {"error": f"Could not find valid ID for series '{series_name}'"}

            # Get episodes for the specified season
            print(f"Getting episodes for series ID {series_id}, season {season}")
            episodes = self.tvdb_client.get_series_episodes_by_season(series_id, season_number=season)

            # Add series name to the response for context
            return {
                "series_name": found_series.get("name", series_name),
                "season_number": season,
                "episodes": episodes
            }

        elif intent == "get_next_aired":
            series_name = params.get("series_name", "")

            # Search for the series
            results = self.tvdb_client.search_series(series_name, limit=1)

            if not results:
                return {"error": f"Could not find series '{series_name}'"}

            # Get the series ID
            series_id_str = results[0].get("id")

            # Extract numeric ID
            if series_id_str and isinstance(series_id_str, str) and series_id_str.startswith("series-"):
                try:
                    series_id = int(series_id_str.replace("series-", ""))
                    return self.tvdb_client.get_series_next_aired(series_id)
                except ValueError:
                    return {"error": f"Invalid series ID format: {series_id_str}"}
            else:
                return {"error": f"Could not find valid ID for series '{series_name}'"}

        elif intent == "get_artwork":
            series_name = params.get("series_name", "")

            # Search for the series
            results = self.tvdb_client.search_series(series_name, limit=1)

            if not results:
                return {"error": f"Could not find series '{series_name}'"}

            # Get the series ID
            series_id_str = results[0].get("id")

            # Extract numeric ID
            if series_id_str and isinstance(series_id_str, str) and series_id_str.startswith("series-"):
                try:
                    series_id = int(series_id_str.replace("series-", ""))
                    return self.tvdb_client.get_series_artworks(series_id)
                except ValueError:
                    return {"error": f"Invalid series ID format: {series_id_str}"}
            else:
                return {"error": f"Could not find valid ID for series '{series_name}'"}

        # Add this to the _handle_intent method in TVSeriesBot class

        elif intent == "get_series_awards":
            series_name = params.get("series_name", "")

            # Ensure we have a series name
            if not series_name:
                return {"error": "Please specify a TV series name to see its awards"}

            print(f"Looking for awards for series: {series_name}")

            # Search for the series
            results = self.tvdb_client.search_series(series_name, limit=1)

            if not results:
                return {"error": f"Could not find series '{series_name}'"}

            # Get full information about the found series
            found_series = results[0]
            series_id_str = found_series.get("id")
            series_id = None

            # Extract numeric ID from different possible formats
            if isinstance(series_id_str, int):
                series_id = series_id_str
            elif isinstance(series_id_str, str):
                if series_id_str.startswith("series-"):
                    try:
                        series_id = int(series_id_str.replace("series-", ""))
                    except ValueError:
                        return {"error": f"Invalid series ID format: {series_id_str}"}
                else:
                    try:
                        series_id = int(series_id_str)
                    except ValueError:
                        return {"error": f"Invalid series ID format: {series_id_str}"}
            else:
                return {"error": f"Could not find valid ID for series '{series_name}'"}

            # Get awards for the series
            print(f"Getting awards for series ID {series_id}")
            awards = self.tvdb_client.get_series_awards(series_id)

            # Add series name to the response for context
            return {
                "series_name": found_series.get("name", series_name),
                "awards": awards
            }

        elif intent == "get_movie_awards":
            movie_name = params.get("movie_name", "")

            # Ensure we have a movie name
            if not movie_name:
                return {"error": "Please specify a movie name to see its awards"}

            # Search for the movie
            results = self.tvdb_client.search_movies(query=movie_name, limit=1)

            if not results:
                return {"error": f"Could not find movie '{movie_name}'"}

            # Get the movie ID
            movie_id_str = results[0].get("id")
            movie_id = None

            # Extract numeric ID
            if isinstance(movie_id_str, int):
                movie_id = movie_id_str
            elif isinstance(movie_id_str, str):
                if movie_id_str.startswith("movie-"):
                    try:
                        movie_id = int(movie_id_str.replace("movie-", ""))
                    except ValueError:
                        return {"error": f"Invalid movie ID format: {movie_id_str}"}
                else:
                    try:
                        movie_id = int(movie_id_str)
                    except ValueError:
                        return {"error": f"Invalid movie ID format: {movie_id_str}"}
            else:
                return {"error": f"Could not find valid ID for movie '{movie_name}'"}

            # Get awards for the movie
            awards = self.tvdb_client.get_movie_awards(movie_id)

            # Add movie name to the response for context
            return {
                "movie_name": results[0].get("name", movie_name),
                "awards": awards
            }

        elif intent == "advanced_search":
            # Extract search parameters
            query = params.get("query", "")
            type = params.get("type")
            year = params.get("year")
            country = params.get("country")
            company = params.get("company")
            director = params.get("director")
            language = params.get("language")
            network = params.get("network")
            primary_type = params.get("primary_type")
            remote_id = params.get("remote_id")

            # Convert year to int if it's a string
            if year and isinstance(year, str) and year.isdigit():
                year = int(year)

            # Perform the advanced search
            results = self.tvdb_client.advanced_search(
                query=query,
                type=type,
                year=year,
                country=country,
                company=company,
                language=language,
                director=director,
                primary_type=primary_type,
                network=network,
                remote_id=remote_id,
                limit=limit
            )

            # Return the search results
            return {
                "search_params": {
                    "query": query,
                    "type": type,
                    "year": year,
                    "country": country,
                    "company": company,
                    "language": language,
                    "director": director,
                    "network": network
                },
                "results": results
            }



        elif intent == "get_character_details":
            character_name = params.get("character_name", "")
            series_name = params.get("series_name", "")

            if not character_name:
                return {"error": "Please specify a character name"}

            # If series name is provided, use it to narrow down the search
            if series_name:
                # Search for the series
                series_results = self.tvdb_client.search_series(series_name, limit=1)

                if not series_results:
                    return {"error": f"Could not find series '{series_name}'"}

                # Get the series ID
                series_id_str = series_results[0].get("id")

                # Extract numeric ID
                if series_id_str and isinstance(series_id_str, str) and series_id_str.startswith("series-"):
                    try:
                        series_id = int(series_id_str.replace("series-", ""))
                        # Get the series details including characters
                        series_details = self.tvdb_client.get_series_details(series_id)

                        # Find the character in the series
                        characters = series_details.get("characters", [])
                        for character in characters:
                            if character_name.lower() in character.get("name", "").lower():
                                return character

                        return {"error": f"Could not find character '{character_name}' in series '{series_name}'"}
                    except ValueError:
                        return {"error": f"Invalid series ID format: {series_id_str}"}

        else:
            # Unknown intent, return help information
            return {
                "help": {
                    "description": "I'm not sure what you're asking for. Here are some things I can help with:",
                    "examples": [
                        "Finding TV series based on genres, actors, or networks",
                        "Getting information about specific TV series",
                        "Finding similar shows to ones you like",
                        "Discovering what shows an actor has been in",
                        "Learning about upcoming series",
                        "Suggestion what to show next",
                    ]
                }
            }
