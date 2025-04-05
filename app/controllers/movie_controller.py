"""Controller for handling movie-related requests."""

from typing import Dict, List, Optional, Any

from app.tvdb.client import TVDBClient
from app.chatbot.llm_service import LLMService
from app.tvdb.models import UserQuery, ConversationContext


class MovieController:
    """Controller for handling movie-related requests."""

    def __init__(self, tvdb_client: TVDBClient, llm_service: LLMService):
        """Initialize the movie controller."""
        self.tvdb_client = tvdb_client
        self.llm_service = llm_service

    def handle_request(
            self,
            query: UserQuery,
            context: Optional[ConversationContext] = None
    ) -> Dict:
        """Handle a movie-related request based on the user's intent."""
        intent = query.intent
        params = query.parameters

        if intent == "search_movies":
            return self._handle_search_movies(params)
        elif intent == "get_movie_details":
            return self._handle_get_movie_details(params)
        elif intent == "get_similar_movies":
            return self._handle_get_similar_movies(params)
        elif intent == "get_movie_by_director":
            return self._handle_get_movies_by_director(params)
        elif intent == "get_movie_awards":
            return self._handle_get_movie_awards(params)
        elif intent == "get_trending_movies":
            return self._handle_get_trending_movies(params)
        elif intent == "recommend_movies":
            return self._handle_recommend_movies(params, context)
        else:
            return {"error": "Unknown movie intent"}

    def _handle_search_movies(self, params: Dict) -> Dict:
        """Handle search_movies intent with improved reliability."""
        movie_name = params.get("movie_name", "")
        year = params.get("year")
        director = params.get("director_name")
        genre = params.get("genre")
        country = params.get("country")
        language = params.get("language")
        limit = params.get("limit", 5)

        # Try to convert year to int if it's a string
        if year and isinstance(year, str):
            try:
                year = int(year)
            except ValueError:
                year = None

        # Convert limit to int if it's a string
        if isinstance(limit, str):
            try:
                limit = int(limit)
            except ValueError:
                limit = 5

        print(f"Movie search request: movie_name='{movie_name}', genre='{genre}', year={year}, director='{director}'")

        # Try specialized search first if we have director
        if director:
            print(f"Searching for movies by director: {director}")
            director_results = self.tvdb_client.get_movies_by_director(director, limit=limit)
            if director_results:
                print(f"Found {len(director_results)} movies by director {director}")
                return {
                    "search_params": {
                        "director_name": director,
                        "movie_name": movie_name,
                        "genre": genre,
                        "year": year
                    },
                    "results": director_results,
                    "count": len(director_results)
                }

        # If we have a specific movie name, use that as the primary search term
        if movie_name:
            results = []

            # Try direct movie search
            print(f"Searching for movies with name: {movie_name}")
            try:
                search_results = self.tvdb_client.search_movies(
                    query=movie_name,
                    year=year,
                    director=director,
                    country=country,
                    language=language,
                    limit=limit
                )

                if search_results:
                    print(f"Found {len(search_results)} results for movie name '{movie_name}'")

                    # Filter by genre if specified
                    if genre and len(search_results) > 0:
                        print(f"Filtering results by genre: {genre}")
                        filtered_results = []
                        for movie in search_results:
                            # Get genre info from the movie
                            movie_genres = movie.get("genres", [])
                            genre_names = []

                            # Extract genre names based on format
                            if movie_genres:
                                if isinstance(movie_genres[0], dict):
                                    genre_names = [g.get("name", "").lower() for g in movie_genres]
                                else:
                                    genre_names = [str(g).lower() for g in movie_genres]

                            # Check if movie matches the genre
                            if genre.lower() in " ".join(genre_names).lower():
                                filtered_results.append(movie)

                        if filtered_results:
                            print(f"Found {len(filtered_results)} results after genre filtering")
                            results = filtered_results
                        else:
                            print(f"No results match genre '{genre}', using unfiltered results")
                            results = search_results
                    else:
                        results = search_results

                    return {
                        "search_params": {
                            "movie_name": movie_name,
                            "year": year,
                            "director": director,
                            "genre": genre,
                            "country": country,
                            "language": language
                        },
                        "results": results,
                        "count": len(results)
                    }
            except Exception as e:
                print(f"Error in movie search: {e}")

        # If we only have a genre, use genre-based search
        if genre and not results:
            print(f"Searching for movies by genre: {genre}")
            genre_results = self.tvdb_client.get_movies_by_genre(genre, limit=limit)
            if genre_results:
                print(f"Found {len(genre_results)} movies in genre {genre}")
                return {
                    "search_params": {
                        "genre": genre,
                        "movie_name": movie_name,
                        "year": year
                    },
                    "results": genre_results,
                    "count": len(genre_results)
                }

        # If all specific searches failed, try the safe search method
        print("Using safe search method as fallback")
        safe_results = self.tvdb_client.safe_search_movies(
            query=movie_name,
            genre=genre,
            year=year,
            limit=limit
        )

        if safe_results:
            print(f"Safe search found {len(safe_results)} results")
            return {
                "search_params": {
                    "movie_name": movie_name,
                    "year": year,
                    "director": director,
                    "genre": genre,
                    "country": country,
                    "language": language
                },
                "results": safe_results,
                "count": len(safe_results),
                "message": "Using alternative search results"
            }

        # If absolutely nothing worked, return empty results with helpful message
        return {
            "search_params": {
                "movie_name": movie_name,
                "year": year,
                "director": director,
                "genre": genre,
                "country": country,
                "language": language
            },
            "results": [],
            "count": 0,
            "error": "No movies found matching your criteria",
            "suggestions": [
                "Try a different movie name",
                "Search for a genre instead (e.g., 'action movies')",
                "Browse trending movies",
                "Search for movies by a specific director"
            ]
        }

    def _handle_get_movie_details(self, params: Dict) -> Dict:
        """Handle get_movie_details intent."""
        movie_name = params.get("movie_name", "")
        movie_id = params.get("movie_id")

        if not movie_id and not movie_name:
            return {"error": "Please specify a movie name or ID"}

        # If we only have the name, search for the movie first
        if not movie_id:
            search_results = self.tvdb_client.search_movies(query=movie_name, limit=1)
            if not search_results:
                return {"error": f"Could not find movie '{movie_name}'"}

            movie_id = search_results[0].get("id")

        # Extract numeric ID if needed
        if isinstance(movie_id, str):
            if movie_id.startswith("movie-"):
                try:
                    movie_id = int(movie_id.replace("movie-", ""))
                except ValueError:
                    return {"error": f"Invalid movie ID format: {movie_id}"}

        # Get movie details
        details = self.tvdb_client.get_movie_details(movie_id)

        if not details:
            return {"error": f"Could not find details for movie ID {movie_id}"}

        # Get additional data
        cast = self.tvdb_client.get_movie_cast(movie_id)
        awards = self.tvdb_client.get_movie_awards(movie_id)

        return {
            "movie": details,
            "cast": cast,
            "awards": awards
        }

    def _handle_get_similar_movies(self, params: Dict) -> Dict:
        """Handle get_similar_movies intent."""
        movie_name = params.get("movie_name", "")
        movie_id = params.get("movie_id")

        if not movie_id and not movie_name:
            return {"error": "Please specify a movie name or ID to find similar movies"}

        # If we only have the name, search for the movie first
        if not movie_id:
            search_results = self.tvdb_client.search_movies(query=movie_name, limit=1)
            if not search_results:
                return {"error": f"Could not find movie '{movie_name}'"}

            movie_id = search_results[0].get("id")

        # Extract numeric ID if needed
        if isinstance(movie_id, str):
            if movie_id.startswith("movie-"):
                try:
                    movie_id = int(movie_id.replace("movie-", ""))
                except ValueError:
                    return {"error": f"Invalid movie ID format: {movie_id}"}

        # Get similar movies
        similar_movies = self.tvdb_client.get_similar_movies(movie_id)

        if not similar_movies:
            return {"error": f"Could not find any similar movies"}

        # Get the original movie details for context
        original_movie = self.tvdb_client.get_movie_details(movie_id)

        return {
            "original_movie": original_movie,
            "similar_movies": similar_movies,
            "count": len(similar_movies)
        }

    def _handle_get_movies_by_director(self, params: Dict) -> Dict:
        """Handle get_movie_by_director intent."""
        director_name = params.get("director_name", "")

        if not director_name:
            return {"error": "Please specify a director name"}

        movies = self.tvdb_client.get_movies_by_director(director_name)

        if not movies:
            return {"error": f"Could not find any movies directed by '{director_name}'"}

        return {
            "director": director_name,
            "movies": movies,
            "count": len(movies)
        }

    def _handle_get_movie_awards(self, params: Dict) -> Dict:
        """Handle get_movie_awards intent."""
        movie_name = params.get("movie_name", "")
        movie_id = params.get("movie_id")

        if not movie_id and not movie_name:
            return {"error": "Please specify a movie name or ID"}

        # If we only have the name, search for the movie first
        if not movie_id:
            search_results = self.tvdb_client.search_movies(query=movie_name, limit=1)
            if not search_results:
                return {"error": f"Could not find movie '{movie_name}'"}

            movie_id = search_results[0].get("id")

        # Extract numeric ID if needed
        if isinstance(movie_id, str):
            if movie_id.startswith("movie-"):
                try:
                    movie_id = int(movie_id.replace("movie-", ""))
                except ValueError:
                    return {"error": f"Invalid movie ID format: {movie_id}"}

        # Get movie awards
        awards = self.tvdb_client.get_movie_awards(movie_id)
        movie_details = self.tvdb_client.get_movie_details(movie_id)

        if not awards:
            movie_name = movie_details.get("name", movie_name)
            return {"warning": f"No awards found for movie '{movie_name}'", "movie": movie_details}

        return {
            "movie": movie_details,
            "awards": awards,
            "count": len(awards)
        }

    def _handle_recommend_movies(self, params: Dict, context: Optional[ConversationContext] = None) -> Dict:
        """Handle recommend_movies intent with improved error handling."""
        # Extract parameters
        genres = params.get("genre", [])
        if genres and not isinstance(genres, list):
            genres = [genres]

        actors = params.get("actor_name", [])
        if actors and not isinstance(actors, list):
            actors = [actors]

        directors = params.get("director_name", [])
        if directors and not isinstance(directors, list):
            directors = [directors]

        # Log what we're doing
        print(f"Movie recommendation request with genres: {genres}, actors: {actors}, directors: {directors}")

        # If no specific criteria, default to trending movies
        if not any([genres, actors, directors]):
            print("No specific criteria provided, fetching trending movies")
            trending_movies = self.tvdb_client.get_trending_movies(limit=5)

            if trending_movies:
                return {
                    "trending_movies": trending_movies,
                    "count": len(trending_movies)
                }
            else:
                # Try a general search for popular movies
                print("No trending movies found, searching for popular movies")
                popular_movies = self.tvdb_client.search_movies(query="popular", limit=5)
                if popular_movies:
                    return {
                        "recommended_movies": popular_movies,
                        "message": "Here are some popular movies you might enjoy",
                        "count": len(popular_movies)
                    }

                # Last resort - try drama genre
                return {
                    "warning": "Couldn't find trending movies, showing drama movies instead",
                    "recommended_movies": self.tvdb_client.search_movies(query="drama", limit=5),
                    "count": 5
                }

        # Get user preferences from context
        if context and context.user_preferences:
            prefs = context.user_preferences

            # Add favorite genres if none specified
            if not genres and prefs.favorite_genres:
                genres.extend(prefs.favorite_genres)
                print(f"Added genres from user preferences: {prefs.favorite_genres}")

            # Add favorite actors if none specified
            if not actors and prefs.favorite_actors:
                actors.extend(prefs.favorite_actors)
                print(f"Added actors from user preferences: {prefs.favorite_actors}")

        # Create criteria dictionary
        criteria = {
            "genres": genres,
            "actors": actors,
            "directors": directors
        }

        # Get recommended movies based on criteria
        print(f"Recommending movies with criteria: {criteria}")
        recommended_movies = self.tvdb_client.recommend_movies(criteria)

        if not recommended_movies:
            print("No movies matched criteria, trying fallback options")

            # Try each genre individually
            if genres:
                for genre in genres:
                    genre_movies = self.tvdb_client.get_movies_by_genre(genre, limit=3)
                    if genre_movies:
                        return {
                            "warning": f"Showing movies in the {genre} genre",
                            "recommended_movies": genre_movies,
                            "count": len(genre_movies)
                        }

            # Try trending as fallback
            trending = self.tvdb_client.get_trending_movies()
            if trending:
                return {
                    "warning": "No movies match your preferences, showing trending movies instead",
                    "recommended_movies": trending,
                    "count": len(trending)
                }

            # Last resort - basic search
            fallback_movies = self.tvdb_client.search_movies(query="movie", limit=5)
            if fallback_movies:
                return {
                    "warning": "Couldn't find specific recommendations, showing general results",
                    "recommended_movies": fallback_movies,
                    "count": len(fallback_movies)
                }

            # Absolutely nothing found
            return {
                "error": "Could not find any movie recommendations at this time",
                "suggestions": [
                    "Try different genres or actors",
                    "Ask for trending movies",
                    "Search for a specific movie title"
                ]
            }

        # Return the successfully recommended movies
        return {
            "criteria": criteria,
            "recommended_movies": recommended_movies,
            "count": len(recommended_movies)
        }

    def _handle_get_trending_movies(self, params: Dict) -> Dict:
        """Handle get_trending_movies intent with improved error handling."""
        limit = int(params.get("limit", 5))
        genre = params.get("genre")

        print(f"Fetching trending movies (limit: {limit}, genre: {genre})")

        # Try to get trending movies
        trending_movies = self.tvdb_client.get_trending_movies(limit=10)

        # If no trending movies, try a fallback search
        if not trending_movies:
            print("No trending movies found, trying fallback search")
            # Fallback: search for recent movies or popular movies
            fallback_movies = self.tvdb_client.search_movies(query="popular", limit=limit)

            if fallback_movies:
                return {
                    "trending_movies": fallback_movies,
                    "fallback": True,
                    "message": "Showing popular movies as trending data is unavailable",
                    "count": len(fallback_movies)
                }

            # Another fallback if the first one fails
            basic_movies = self.tvdb_client.search_movies(query="movie", limit=limit)
            if basic_movies:
                return {
                    "trending_movies": basic_movies,
                    "fallback": True,
                    "message": "Showing general movie results as trending data is unavailable",
                    "count": len(basic_movies)
                }

            # No results found
            return {
                "error": "Could not find any trending movies",
                "suggestions": [
                    "Try searching for specific movie titles",
                    "Search by genre (e.g., 'action movies')",
                    "Search by actor or director"
                ]
            }

        # Filter by genre if specified
        if genre:
            print(f"Filtering trending movies by genre: {genre}")
            filtered_movies = []
            for movie in trending_movies:
                movie_genres = movie.get("genres", [])
                genre_names = []

                # Extract genre names from different formats
                if movie_genres:
                    if isinstance(movie_genres[0], dict):
                        genre_names = [g.get("name", "").lower() for g in movie_genres]
                    else:
                        genre_names = [g.lower() for g in movie_genres]

                if genre.lower() in genre_names:
                    filtered_movies.append(movie)

            if filtered_movies:
                trending_movies = filtered_movies
                print(f"Found {len(filtered_movies)} {genre} movies")
            else:
                print(f"No trending movies found for genre: {genre}")
                # If no movies match the genre, try a direct genre search
                genre_movies = self.tvdb_client.get_movies_by_genre(genre, limit=limit)
                if genre_movies:
                    return {
                        "trending_movies": genre_movies,
                        "genre_filter": genre,
                        "fallback": True,
                        "message": f"Showing {genre} movies as no trending {genre} movies were found",
                        "count": len(genre_movies)
                    }

        # Limit results and return
        trending_movies = trending_movies[:limit]
        return {
            "trending_movies": trending_movies,
            "genre_filter": genre,
            "count": len(trending_movies)
        }
