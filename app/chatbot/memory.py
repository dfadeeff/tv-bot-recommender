"""Memory module for maintaining conversation context."""

from typing import Dict, List, Optional, Any
import uuid
from datetime import datetime, timedelta

from app.tvdb.models import ConversationContext, UserQuery, UserPreference


class ConversationMemory:
    """Memory class for maintaining conversation context."""

    def __init__(self, max_history: int = 10, session_ttl_hours: int = 24):
        """Initialize the conversation memory.

        Args:
            max_history: Maximum number of queries to store in history
            session_ttl_hours: Time-to-live for sessions in hours
        """
        self.sessions: Dict[str, Dict] = {}
        self.max_history = max_history
        self.session_ttl = session_ttl_hours

    def get_or_create_session(self, session_id: Optional[str] = None) -> str:
        """Get an existing session or create a new one.

        Args:
            session_id: Optional session ID

        Returns:
            Session ID
        """
        # If session ID is provided and exists, return it
        if session_id and session_id in self.sessions:
            # Update last accessed time
            self.sessions[session_id]["last_accessed"] = datetime.now()
            return session_id

        # Otherwise, create a new session
        new_session_id = str(uuid.uuid4())
        self.sessions[new_session_id] = {
            "context": ConversationContext(
                queryHistory=[],
                userPreferences=UserPreference(),
                lastSeriesContext=[]
            ),
            "created_at": datetime.now(),
            "last_accessed": datetime.now()
        }

        return new_session_id

    def add_query(self, session_id: str, query: UserQuery) -> None:
        """Add a new query to the conversation history.

        Args:
            session_id: Session ID
            query: User query to add
        """
        # Ensure session exists
        if session_id not in self.sessions:
            session_id = self.get_or_create_session()

        # Update last accessed time
        self.sessions[session_id]["last_accessed"] = datetime.now()

        # Get context
        context = self.sessions[session_id]["context"]

        # Add query to history
        context.query_history.append(query)

        # Keep history within the maximum limit
        if len(context.query_history) > self.max_history:
            context.query_history = context.query_history[-self.max_history:]

        # Update user preferences based on the query
        self._update_preferences_from_query(session_id, query)

    def set_last_series_context(self, session_id: str, series_ids: List[int]) -> None:
        """Set the last series context.

        Args:
            session_id: Session ID
            series_ids: List of series IDs
        """
        # Ensure session exists
        if session_id not in self.sessions:
            session_id = self.get_or_create_session()

        # Update last accessed time
        self.sessions[session_id]["last_accessed"] = datetime.now()

        # Set last series context
        self.sessions[session_id]["context"].last_series_context = series_ids

    def get_context(self, session_id: str) -> ConversationContext:
        """Get the current conversation context.

        Args:
            session_id: Session ID

        Returns:
            Current conversation context
        """
        # Ensure session exists
        if session_id not in self.sessions:
            session_id = self.get_or_create_session()

        # Update last accessed time
        self.sessions[session_id]["last_accessed"] = datetime.now()

        return self.sessions[session_id]["context"]

    def _update_preferences_from_query(self, session_id: str, query: UserQuery) -> None:
        """Update user preferences based on the query.

        Args:
            session_id: Session ID
            query: User query
        """
        # Ensure session exists
        if session_id not in self.sessions:
            return

        context = self.sessions[session_id]["context"]
        params = query.parameters

        # Update genre preferences
        if 'genre' in params and params['genre']:
            genre = params['genre']
            if genre not in context.user_preferences.favorite_genres:
                context.user_preferences.favorite_genres.append(genre)

        # Update actor preferences
        if 'actor_name' in params and params['actor_name']:
            actor = params['actor_name']
            if actor not in context.user_preferences.favorite_actors:
                context.user_preferences.favorite_actors.append(actor)

        # Update network preferences
        if 'network' in params and params['network']:
            network = params['network']
            if network not in context.user_preferences.preferred_networks:
                context.user_preferences.preferred_networks.append(network)

    def update_preferences(
            self,
            session_id: str,
            genres: Optional[List[str]] = None,
            series_ids: Optional[List[int]] = None,
            actors: Optional[List[str]] = None,
            networks: Optional[List[str]] = None
    ) -> None:
        """Explicitly update user preferences.

        Args:
            session_id: Session ID
            genres: List of genre names
            series_ids: List of series IDs
            actors: List of actor names
            networks: List of network names
        """
        # Ensure session exists
        if session_id not in self.sessions:
            session_id = self.get_or_create_session()

        # Update last accessed time
        self.sessions[session_id]["last_accessed"] = datetime.now()

        context = self.sessions[session_id]["context"]

        if genres:
            for genre in genres:
                if genre not in context.user_preferences.favorite_genres:
                    context.user_preferences.favorite_genres.append(genre)

        if series_ids:
            for series_id in series_ids:
                if series_id not in context.user_preferences.favorite_series:
                    context.user_preferences.favorite_series.append(series_id)

        if actors:
            for actor in actors:
                if actor not in context.user_preferences.favorite_actors:
                    context.user_preferences.favorite_actors.append(actor)

        if networks:
            for network in networks:
                if network not in context.user_preferences.preferred_networks:
                    context.user_preferences.preferred_networks.append(network)

    def clear_session(self, session_id: str) -> None:
        """Clear a specific session.

        Args:
            session_id: Session ID to clear
        """
        if session_id in self.sessions:
            del self.sessions[session_id]

    def cleanup_old_sessions(self) -> None:
        """Clean up old sessions based on TTL."""
        now = datetime.now()
        expired_sessions = []

        for session_id, session_data in self.sessions.items():
            last_accessed = session_data["last_accessed"]
            if now - last_accessed > timedelta(hours=self.session_ttl):
                expired_sessions.append(session_id)

        for session_id in expired_sessions:
            self.clear_session(session_id)