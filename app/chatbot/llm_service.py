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
        You are an assistant that helps parse user queries about TV series and movies into structured intents and parameters.
        Your task is to analyze the query and extract the user's intent and any relevant parameters.

        Possible intents:
        # TV Series intents
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
        - get_series_awards: User wants to know what awards a TV series has won or been nominated for
        
        # Movie intents
        - search_movies: User wants to find movies based on criteria (e.g., "Find action movies")
        - get_movie_details: User wants detailed information about a specific movie (e.g., "Tell me about The Matrix")
        - get_similar_movies: User wants recommendations similar to a specific movie (e.g., "Movies like The Godfather")
        - get_movie_by_director: User wants movies by a specific director (e.g., "Christopher Nolan films")
        - get_movie_awards: User wants to know what awards a movie has won (e.g., "What awards did Parasite win?")
        - get_trending_movies: User wants to know popular or trending movies (e.g., "What are the popular movies now?")
        - recommend_movies: User wants movie recommendations (e.g., "Recommend me a movie" or "Suggest a good movie to watch")
        
        # General intents
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
        - movie_name: Name of the movie
        - actor_name: Name of the actor
        - character_name: Name of the character
        - director_name: Name of the director
        - genre: Genre of interest
        - network: TV network
        - season: Season number
        - episode: Episode number
        - year: Year of release
        - status: Status of the series (upcoming, ongoing, ended)
        - country: Country of origin
        - language: Language of interest
        - sort_by: How to sort results (popularity, name, firstAired, etc.)

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
        
        IMPORTANT RULES FOR MOVIES:
        - If the query contains words like "movie", "film", "watch", or is asking for a recommendation without specifying TV shows, prefer the movie-related intents.
        - For general recommendation requests like "recommend something to watch" or "suggest a good film", use the "recommend_movies" intent.
        - If the user asks for "trending" or "popular" content without specifying TV shows, use "get_trending_movies" intent.
        - Queries like "What's a good movie?" or "Can you recommend a film?" should use the "recommend_movies" intent.
        - If the query is specifically about actors or directors in relation to movies, use the corresponding movie intent.
        
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
        """Generate a natural language response to the user's query with token limit handling.

        Args:
            query: Parsed user query
            search_results: Results from the TVDB API
            conversation_context: Current conversation context (optional)

        Returns:
            Natural language response
        """
        # Build the prompt for the LLM
        system_message = """
        You are a helpful TV and movie recommendation assistant that provides information based on TVDB API data.
        Your task is to generate a natural, conversational response to the user's query based on the search results.

        Keep your responses friendly, informative, and focused on the data provided.
        - Highlight key information like genres, cast, ratings, and air dates.
        - If recommending multiple series or movies, explain briefly why each one matches their interests.
        - If the search returned no results, acknowledge this and suggest alternatives or better search terms.
        - Keep responses concise but informative, focusing on the most relevant details.

        For TV series:
        - Include network, status (ended/ongoing), and number of seasons if available
        - Mention notable cast members if provided
        - For episode queries, format them clearly with episode numbers, titles, and brief descriptions

        For movies:
        - Include release year, director, and runtime if available
        - Mention key cast members if provided
        - Highlight any awards or nominations if relevant to the query

        Always base your responses solely on the provided TVDB data. Do not make up information about TV series or movies.
        """

        # Format search results with limiting for large datasets
        formatted_results = self._format_search_results_with_limits(search_results, query.intent)

        # Prepare the input data for the LLM
        input_data = {
            "query": {
                "text": query.query_text,
                "intent": query.intent,
                "parameters": query.parameters
            },
            "search_results": formatted_results
        }

        # Include conversation context if available
        if conversation_context:
            # Add recent conversation history (limited to the most recent query for token savings)
            history = conversation_context.query_history[-1:] if conversation_context.query_history else []

            if history:
                input_data["conversation_history"] = [
                    {"query": q.query_text, "intent": q.intent}
                    for q in history
                ]

            # Add user preferences
            prefs = conversation_context.user_preferences
            if any([prefs.favorite_genres, prefs.favorite_series, prefs.favorite_actors, prefs.preferred_networks]):
                input_data["user_preferences"] = {
                    "favorite_genres": prefs.favorite_genres[:3] if len(
                        prefs.favorite_genres) > 3 else prefs.favorite_genres,
                    "favorite_actors": prefs.favorite_actors[:3] if len(
                        prefs.favorite_actors) > 3 else prefs.favorite_actors,
                    "preferred_networks": prefs.preferred_networks[:2] if len(
                        prefs.preferred_networks) > 2 else prefs.preferred_networks
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
            # Check if it's a token limit error
            error_msg = str(e)
            if "context_length_exceeded" in error_msg or "maximum context length" in error_msg:
                # Try again with more aggressive limiting
                try:
                    # Create a more limited version of the results
                    more_limited_results = self._format_search_results_with_extreme_limits(search_results, query.intent)

                    # Update input data with more limited results
                    input_data["search_results"] = more_limited_results

                    # Simplify other parts of the input
                    if "conversation_history" in input_data:
                        del input_data["conversation_history"]
                    if "user_preferences" in input_data:
                        del input_data["user_preferences"]

                    # Create new simplified input text
                    simplified_input = json.dumps(input_data, indent=2)

                    # Try the API call again with simplified data
                    retry_messages = [
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": simplified_input}
                    ]

                    retry_response = self.client.chat.completions.create(
                        model=self.model,
                        messages=retry_messages,
                        temperature=0.7,
                        max_tokens=800
                    )

                    return retry_response.choices[0].message.content
                except Exception as retry_error:
                    print(f"Error in retry attempt: {retry_error}")
                    return "I found information about this movie but couldn't process all the details due to the large amount of data. Please try asking about specific aspects like the plot, director, or main cast."

            # Handle any other API errors
            print(f"Error calling OpenAI API: {e}")
            return "I'm having trouble generating a response right now. Please try again later."

    def _format_search_results_with_limits(self, results: Any, intent: str) -> Dict:
        """Format search results with limits on large data sets to prevent token limit issues.

        Args:
            results: Results from the TVDB API
            intent: User's intent

        Returns:
            Formatted search results with size limits
        """
        # First get the normally formatted results
        formatted_results = self._format_search_results(results, intent)

        # Apply limits to large arrays in the results
        if isinstance(formatted_results, dict):
            # Limit cast information
            if "cast" in formatted_results and isinstance(formatted_results["cast"], list):
                # Keep only the top cast members (likely the stars)
                formatted_results["cast"] = formatted_results["cast"][:10]
                if len(formatted_results["cast"]) == 10:
                    formatted_results["cast_note"] = "Showing top 10 cast members only"

            # Limit movie object
            if "movie" in formatted_results and isinstance(formatted_results["movie"], dict):
                # Trim large text fields if needed
                if "overview" in formatted_results["movie"] and isinstance(formatted_results["movie"]["overview"],
                                                                           str) and len(
                        formatted_results["movie"]["overview"]) > 500:
                    formatted_results["movie"]["overview"] = formatted_results["movie"]["overview"][:500] + "..."

                # Limit characters/cast in movie details
                if "characters" in formatted_results["movie"] and isinstance(formatted_results["movie"]["characters"],
                                                                             list):
                    formatted_results["movie"]["characters"] = formatted_results["movie"]["characters"][:10]

            # Limit lists of movies
            for key in ["recommended_movies", "similar_movies", "trending_movies", "movies", "results"]:
                if key in formatted_results and isinstance(formatted_results[key], list):
                    # Keep only a reasonable number of movies
                    formatted_results[key] = formatted_results[key][:5]

                    # For each movie, trim large text fields
                    for movie in formatted_results[key]:
                        if isinstance(movie, dict):
                            if "overview" in movie and isinstance(movie["overview"], str) and len(
                                    movie["overview"]) > 300:
                                movie["overview"] = movie["overview"][:300] + "..."

                            # Remove very large arrays that aren't critical
                            for large_field in ["characters", "episodes", "seasons", "translations"]:
                                if large_field in movie and isinstance(movie[large_field], list) and len(
                                        movie[large_field]) > 5:
                                    movie[large_field] = movie[large_field][:5]
                                    movie[f"{large_field}_count"] = len(movie[large_field])

        return formatted_results

    def _format_search_results_with_extreme_limits(self, results: Any, intent: str) -> Dict:
        """Format search results with extreme limits for very large datasets.

        Args:
            results: Results from the TVDB API
            intent: User's intent

        Returns:
            Heavily trimmed search results
        """
        # Start with the limited version
        formatted_results = self._format_search_results_with_limits(results, intent)

        # Apply more extreme limits
        if isinstance(formatted_results, dict):
            # For cast information, keep only essential info about top 5
            if "cast" in formatted_results and isinstance(formatted_results["cast"], list):
                simplified_cast = []
                for cast_member in formatted_results["cast"][:5]:
                    if isinstance(cast_member, dict):
                        # Keep only name and character name
                        simplified_cast.append({
                            "name": cast_member.get("name", cast_member.get("personName", "Unknown")),
                            "character": cast_member.get("character", cast_member.get("characterName", ""))
                        })
                formatted_results["cast"] = simplified_cast
                formatted_results["cast_note"] = "Showing only top 5 cast members with limited details"

            # For movie details, keep only the most essential information
            if "movie" in formatted_results and isinstance(formatted_results["movie"], dict):
                essential_keys = ["id", "name", "title", "year", "overview", "runtime", "genres", "status"]
                movie_essentials = {}
                for key in essential_keys:
                    if key in formatted_results["movie"]:
                        # For overview, limit to a brief summary
                        if key == "overview" and isinstance(formatted_results["movie"][key], str):
                            movie_essentials[key] = formatted_results["movie"][key][:200] + "..." if len(
                                formatted_results["movie"][key]) > 200 else formatted_results["movie"][key]
                        # For genres, keep only names
                        elif key == "genres" and isinstance(formatted_results["movie"][key], list):
                            if formatted_results["movie"][key] and isinstance(formatted_results["movie"][key][0], dict):
                                movie_essentials[key] = [g.get("name", "") for g in formatted_results["movie"][key][:3]]
                            else:
                                movie_essentials[key] = formatted_results["movie"][key][:3]
                        else:
                            movie_essentials[key] = formatted_results["movie"][key]

                formatted_results["movie"] = movie_essentials

            # Extremely limit movie lists
            for key in ["recommended_movies", "similar_movies", "trending_movies", "movies", "results"]:
                if key in formatted_results and isinstance(formatted_results[key], list):
                    simplified_movies = []
                    for movie in formatted_results[key][:3]:  # Keep only top 3
                        if isinstance(movie, dict):
                            # Keep only essential information
                            simplified_movie = {
                                "name": movie.get("name", movie.get("title", "Unknown")),
                                "year": movie.get("year", ""),
                                "id": movie.get("id", "")
                            }

                            # Add a brief overview if available
                            if "overview" in movie and isinstance(movie["overview"], str):
                                simplified_movie["overview"] = movie["overview"][:150] + "..." if len(
                                    movie["overview"]) > 150 else movie["overview"]

                            # Add genres if available (simplified)
                            if "genres" in movie and isinstance(movie["genres"], list):
                                if movie["genres"] and isinstance(movie["genres"][0], dict):
                                    simplified_movie["genres"] = [g.get("name", "") for g in movie["genres"][:2]]
                                else:
                                    simplified_movie["genres"] = movie["genres"][:2]

                            simplified_movies.append(simplified_movie)

                    formatted_results[key] = simplified_movies
                    formatted_results[f"{key}_note"] = "Showing limited information for top movies only"

        return formatted_results

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

        # Handle error messages in results
        if isinstance(results, dict) and "error" in results:
            return results

        # Special handling for movie-related intents
        if intent in ["search_movies", "get_movie_details", "get_similar_movies", "get_trending_movies",
                      "recommend_movies"]:
            if isinstance(results, dict):
                # Check for movie-specific fields and normalize them
                if "movie" in results:
                    # Single movie with details
                    return self._format_movie_result(results)
                elif "recommended_movies" in results:
                    # Movie recommendations
                    return {
                        "recommended_movies": [self._format_movie_object(m) for m in
                                               results.get("recommended_movies", [])],
                        "criteria": results.get("criteria", {}),
                        "count": results.get("count", 0)
                    }
                elif "similar_movies" in results:
                    # Similar movies
                    return {
                        "original_movie": self._format_movie_object(results.get("original_movie", {})),
                        "similar_movies": [self._format_movie_object(m) for m in results.get("similar_movies", [])],
                        "count": results.get("count", 0)
                    }
                elif "trending_movies" in results:
                    # Trending movies
                    return {
                        "trending_movies": [self._format_movie_object(m) for m in results.get("trending_movies", [])],
                        "genre_filter": results.get("genre_filter", ""),
                        "count": results.get("count", 0)
                    }
                elif "results" in results:
                    # Search results
                    movies = results.get("results", [])
                    return {
                        "search_params": results.get("search_params", {}),
                        "movies": [self._format_movie_object(m) for m in movies],
                        "count": len(movies)
                    }

        # Special handling for episode results
        if intent == "get_series_episodes" and isinstance(results, dict):
            # Format episode data for clearer presentation
            formatted_results = {
                "series_name": results.get("series_name", "Unknown Series"),
                "season_number": results.get("season_number", "All Seasons"),
                "episodes_count": len(results.get("episodes", [])),
                "episodes": []
            }

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

    def _format_movie_result(self, result: Dict) -> Dict:
        """Format a single movie result for more consistent LLM processing.

        Args:
            result: Movie result data

        Returns:
            Formatted movie data
        """
        formatted = {}

        # Handle common movie result formats
        if "movie" in result:
            formatted["movie"] = self._format_movie_object(result["movie"])

        if "cast" in result:
            formatted["cast"] = result["cast"]

        if "awards" in result:
            formatted["awards"] = result["awards"]

        # Add any other keys
        for key, value in result.items():
            if key not in formatted:
                formatted[key] = value

        return formatted

    def _format_movie_object(self, movie: Dict) -> Dict:
        """Format a movie object to ensure consistent fields.

        Args:
            movie: Movie object data

        Returns:
            Formatted movie object
        """
        if not movie:
            return {}

        formatted = {
            "id": movie.get("id", ""),
            "name": movie.get("name", movie.get("title", "")),
            "type": "movie"
        }

        # Copy all other fields
        for key, value in movie.items():
            if key not in formatted:
                formatted[key] = value

        return formatted
