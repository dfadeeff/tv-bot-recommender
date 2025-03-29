"""LLM service for natural language understanding and generation."""

import json
import os
from typing import Dict, List, Optional, Any, Tuple

from openai import OpenAI
from dotenv import load_dotenv

from app.tvdb.models import UserQuery, ConversationContext

# Load environment variables
load_dotenv()

# Get OpenAI API key from environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)


class LLMService:
    """Service for natural language understanding and generation."""

    def __init__(self, model: str = OPENAI_MODEL):
        """Initialize the LLM service."""
        self.model = model
        self.client = OpenAI(api_key=OPENAI_API_KEY)

    def parse_user_intent(
            self,
            query: str,
            conversation_context: Optional[ConversationContext] = None
    ) -> UserQuery:
        """Parse the user's query to determine their intent and extract parameters.

        Args:
            query: User's query text
            conversation_context: Current conversation context (optional)

        Returns:
            Parsed user query with intent and parameters
        """
        # Build the prompt for the LLM
        print(f"LLM Service: Attempting to parse query: '{query}'")

        system_message = """
        You are an assistant that helps parse user queries about TV series into structured intents and parameters.
        Your task is to analyze the query and extract the user's intent and any relevant parameters.

        Possible intents:
        - search_series: User wants to find TV series based on criteria
        - get_series_details: User wants detailed information about a specific series
        - get_similar_series: User wants recommendations similar to a specific series
        - get_actor_filmography: User wants to know what series an actor has been in
        - get_series_by_network: User wants series from a specific network
        - get_upcoming_series: User wants to know about upcoming series
        - get_series_episodes: User wants to know about episodes of a series
        - get_next_aired: User wants to know when the next episode will air
        - get_season_details: User wants information about a specific season
        - get_character_details: User wants information about a character
        - get_artwork: User wants to see images or artwork for a series
        - update_preferences: User is sharing their preferences
        - help: User needs help using the system
        - search_series: User wants to find TV series based on criteria
        - get_series_details: User wants detailed information about a specific series
        - get_similar_series: User wants recommendations similar to a specific series
        - get_actor_filmography: User wants to know what series an actor has been in
        - get_series_by_network: User wants series from a specific network
        - get_upcoming_series: User wants to know about upcoming series
        - get_series_episodes: User wants to know about episodes of a series
        - get_next_aired: User wants to know when the next episode will air
        - get_season_details: User wants information about a specific season
        - get_character_details: User wants information about a character
        - get_artwork: User wants to see images or artwork for a series
        - get_series_awards: User wants to know what awards a TV series has won or been nominated for
        - get_movie_awards: User wants to know what awards a movie has won or been nominated for
        - advanced_search: User wants to search with multiple criteria or filters
        - update_preferences: User is sharing their preferences
        - help: User needs help using the system

        
        
        Keep your responses friendly, informative, and focused on the data provided.
        - Highlight key information like genres, cast, ratings, and air dates.
        - If recommending multiple series, explain briefly why each one matches their interests.
        - If the search returned no results, acknowledge this and suggest alternatives or better search terms.
        - Keep responses concise but informative, focusing on the most relevant details.
        
        For episode queries:
        - When listing episodes, format them clearly with episode numbers, titles, and brief descriptions.
        - For season-specific queries, mention the season number in your response.
        - If there are many episodes, summarize the first few and the total count instead of listing them all.
        - Highlight notable episodes if that information is available.
        
        Always base your responses solely on the provided TVDB data. Do not make up information about TV series.

        Parameters to extract (when applicable):
        - series_name: Name of the TV series
        - actor_name: Name of the actor
        - character_name: Name of the character
        - genre: Genre of interest
        - network: TV network
        - season: Season number
        - episode: Episode number
        - year: Year of release
        - status: Status of the series (upcoming, ongoing, ended)
        - country: Country of origin
        - language: Language of interest
        - sort_by: How to sort results (popularity, name, firstAired, etc.)
        - series_name: Name of the TV series
        - movie_name: Name of the movie
        - actor_name: Name

        Return a JSON object with the following structure:
        {
            "intent": "intent_name",
            "parameters": {
                "param1": "value1",
                "param2": "value2",
                ...
            }
        }

        If a parameter is mentioned but its value is ambiguous, include it with a null value.
        If the intent is unclear, use "help" as the default intent.
        """

        # Include conversation history if available
        history_text = ""
        if conversation_context and conversation_context.query_history:
            history = conversation_context.query_history[-3:] if conversation_context.query_history else []

            if history:
                history_text = "Previous messages in the conversation:\n"
                for i, prev_query in enumerate(history):
                    history_text += f"User {i + 1}: {prev_query.query_text}\n"
                history_text += "\nThe user's current query is: " + query

            # Include known preferences
            prefs = conversation_context.user_preferences
            if any([prefs.favorite_genres, prefs.favorite_series, prefs.favorite_actors, prefs.preferred_networks]):
                history_text += "\n\nKnown user preferences:\n"

                if prefs.favorite_genres:
                    history_text += f"- Favorite genres: {', '.join(prefs.favorite_genres)}\n"
                if prefs.favorite_actors:
                    history_text += f"- Favorite actors: {', '.join(prefs.favorite_actors)}\n"
                if prefs.preferred_networks:
                    history_text += f"- Preferred networks: {', '.join(prefs.preferred_networks)}\n"

        # Create the messages for the API call
        messages = [
            {"role": "system", "content": system_message}
        ]

        if history_text:
            messages.append({"role": "user", "content": history_text})
        else:
            messages.append({"role": "user", "content": query})

        try:
            print(f"LLM Service: Making API call to OpenAI")
            # Make the API call
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.2,  # Low temperature for more deterministic outputs
                max_tokens=300
            )
            print(f"LLM Service: OpenAI API call successful")

            # Parse the response
            content = response.choices[0].message.content

            # Try to extract JSON from the response
            try:
                # Find JSON in the response
                content = content.strip()
                start_idx = content.find("{")
                end_idx = content.rfind("}") + 1

                if start_idx >= 0 and end_idx > start_idx:
                    json_str = content[start_idx:end_idx]
                    parsed_data = json.loads(json_str)

                    # Ensure required fields are present
                    if "intent" not in parsed_data:
                        parsed_data["intent"] = "help"
                    if "parameters" not in parsed_data:
                        parsed_data["parameters"] = {}

                    return UserQuery(
                        queryText=query,
                        intent=parsed_data["intent"],
                        parameters=parsed_data["parameters"]
                    )
            except (json.JSONDecodeError, ValueError) as e:
                print(f"Error parsing LLM response: {str(e)}")
                print(f"Raw response: {content}")
                # If JSON parsing fails, default to help intent
                pass

            # Fallback if JSON parsing fails
            return UserQuery(
                queryText=query,
                intent="help",
                parameters={}
            )

        except Exception as e:
            # Handle any API errors
            print(f"Error calling OpenAI API: {str(e)}")
            return UserQuery(
                queryText=query,
                intent="help",
                parameters={}
            )

    def generate_response(
            self,
            query: UserQuery,
            search_results: Any,
            conversation_context: Optional[ConversationContext] = None
    ) -> str:
        """Generate a natural language response to the user's query.

        Args:
            query: Parsed user query
            search_results: Results from the TVDB API
            conversation_context: Current conversation context (optional)

        Returns:
            Natural language response
        """
        # Build the prompt for the LLM
        system_message = """
        You are a helpful TV series recommendation assistant that provides information based on TVDB API data.
        Your task is to generate a natural, conversational response to the user's query based on the search results.

        Keep your responses friendly, informative, and focused on the data provided.
        - Highlight key information like genres, cast, ratings, and air dates.
        - If recommending multiple series, explain briefly why each one matches their interests.
        - If the search returned no results, acknowledge this and suggest alternatives or better search terms.
        - Keep responses concise but informative, focusing on the most relevant details.

        Always base your responses solely on the provided TVDB data. Do not make up information about TV series.
        """

        # Prepare the input data for the LLM
        input_data = {
            "query": {
                "text": query.query_text,
                "intent": query.intent,
                "parameters": query.parameters
            },
            "search_results": self._format_search_results(search_results, query.intent)
        }

        # Include conversation context if available
        if conversation_context:
            # Add recent conversation history
            history = conversation_context.query_history[-3:] if conversation_context.query_history else []

            if history:
                input_data["conversation_history"] = [
                    {"query": q.query_text, "intent": q.intent}
                    for q in history
                ]

            # Add user preferences
            prefs = conversation_context.user_preferences
            if any([prefs.favorite_genres, prefs.favorite_series, prefs.favorite_actors, prefs.preferred_networks]):
                input_data["user_preferences"] = {
                    "favorite_genres": prefs.favorite_genres,
                    "favorite_actors": prefs.favorite_actors,
                    "preferred_networks": prefs.preferred_networks
                }

        # Format the input data as a string
        input_text = json.dumps(input_data, indent=2)

        # Create the messages for the API call
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": input_text}
        ]

        try:
            # Make the API call
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,  # Higher temperature for more varied responses
                max_tokens=800
            )

            # Return the response
            return response.choices[0].message.content

        except Exception as e:
            # Handle any API errors
            print(f"Error calling OpenAI API: {str(e)}")
            return "I'm having trouble generating a response right now. Please try again later."

    # Add this to your LLMService class

    def _format_search_results(self, results: Any, intent: str) -> Dict:
        """Format search results for the LLM in a consistent structure.

        Args:
            results: Results from the TVDB API
            intent: User's intent

        Returns:
            Formatted search results
        """
        # Handle unexpected string results
        if isinstance(results, str):
            print(f"Warning: Received string instead of object: {results}")
            return {"error": "Unexpected string response", "message": results}

        # Special handling for episode results
        if intent == "get_series_episodes" and isinstance(results, dict):
            # Format episode data for clearer presentation
            formatted_results = {
                "series_name": results.get("series_name", "Unknown Series"),
                "season_number": results.get("season_number", "All Seasons"),
                "episodes_count": len(results.get("episodes", [])),
                "episodes": []
            }

            # Print debug info
            print(f"Formatting {formatted_results['episodes_count']} episodes for {formatted_results['series_name']}")

            # Sort episodes by number if available
            episodes = sorted(
                results.get("episodes", []),
                key=lambda x: (
                    x.get("number", x.get("episodeNumber", x.get("seasonNumber", 999))),
                    x.get("name", "")
                )
            )

            # Format each episode with consistent fields
            for episode in episodes:
                # Try various possible field names
                ep_num = episode.get("number", episode.get("episodeNumber", "?"))
                title = episode.get("name", "Untitled")
                overview = episode.get("overview", "")
                air_date = episode.get("aired", episode.get("firstAired", "Unknown"))

                formatted_episode = {
                    "episode_number": ep_num,
                    "title": title,
                    "overview": overview if overview else "No description available",
                    "aired": air_date
                }
                formatted_results["episodes"].append(formatted_episode)

            if not formatted_results["episodes"]:
                # Add error message if no episodes found
                formatted_results[
                    "error"] = f"No episodes found for season {formatted_results['season_number']} of {formatted_results['series_name']}"
                formatted_results["suggestions"] = [
                    "Try a different season number",
                    "Check if the season exists for this series",
                    "Try searching for the series with a more specific name"
                ]

            return formatted_results

        # If results is already a dictionary or list, return it directly
        if isinstance(results, (dict, list)):
            return results

        # Otherwise, convert to a dictionary
        return {"data": results if results else []}
