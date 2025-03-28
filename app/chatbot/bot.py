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
        limit = 5

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
                        "Learning about upcoming series"
                    ]
                }
            }
