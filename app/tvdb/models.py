"""Data models for the TV Series Recommender."""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class Genre(BaseModel):
    """Genre model."""

    id: int
    name: str
    slug: str


class Network(BaseModel):
    """Network model."""

    id: int
    name: str
    country: Optional[str] = None
    slug: Optional[str] = None


class Character(BaseModel):
    """Character model."""

    id: int
    name: str
    people_id: int = Field(..., alias="peopleId")
    series_id: int = Field(..., alias="seriesId")
    sort: Optional[int] = None
    episode_id: Optional[int] = Field(None, alias="episodeId")
    type: Optional[int] = None
    image: Optional[str] = None
    url: Optional[str] = None
    name_translated: Optional[Dict[str, str]] = Field(None, alias="nameTranslated")
    overview: Optional[str] = None
    people_type: Optional[str] = Field(None, alias="peopleType")

    class Config:
        """Pydantic config."""

        populate_by_name = True


class Season(BaseModel):
    """Season model."""

    id: int
    series_id: int = Field(..., alias="seriesId")
    number: int
    name: Optional[str] = None
    image_url: Optional[str] = Field(None, alias="imageUrl")
    episodes: Optional[List[Dict[str, Any]]] = None

    class Config:
        """Pydantic config."""

        populate_by_name = True


class Episode(BaseModel):
    """Episode model."""

    id: int
    series_id: int = Field(..., alias="seriesId")
    season_id: int = Field(..., alias="seasonId")
    name: str
    aired: Optional[str] = None
    runtime: Optional[int] = None
    overview: Optional[str] = None
    season_number: int = Field(..., alias="seasonNumber")
    episode_number: int = Field(..., alias="number")
    image_url: Optional[str] = Field(None, alias="imageUrl")

    class Config:
        """Pydantic config."""

        populate_by_name = True


class Series(BaseModel):
    """TV Series model."""

    id: int
    name: str
    slug: str
    status: Optional[str] = None
    original_network: Optional[Network] = Field(None, alias="originalNetwork")
    overview: Optional[str] = None
    first_aired: Optional[str] = Field(None, alias="firstAired")
    last_aired: Optional[str] = Field(None, alias="lastAired")
    image_url: Optional[str] = Field(None, alias="image")
    score: Optional[float] = None
    genres: Optional[List[Genre]] = None
    seasons: Optional[List[Season]] = None
    characters: Optional[List[Character]] = None

    class Config:
        """Pydantic config."""

        populate_by_name = True


class UserPreference(BaseModel):
    """User preference model."""

    favorite_genres: List[str] = Field(default_factory=list, alias="favoriteGenres")
    favorite_series: List[int] = Field(default_factory=list, alias="favoriteSeries")
    favorite_actors: List[str] = Field(default_factory=list, alias="favoriteActors")
    preferred_networks: List[str] = Field(default_factory=list, alias="preferredNetworks")

    class Config:
        """Pydantic config."""

        populate_by_name = True


class UserQuery(BaseModel):
    """User query model."""

    query_text: str = Field(..., alias="queryText")
    intent: str
    parameters: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        """Pydantic config."""

        populate_by_name = True


class ConversationContext(BaseModel):
    """Conversation context model."""

    query_history: List[UserQuery] = Field(default_factory=list, alias="queryHistory")
    user_preferences: UserPreference = Field(default_factory=UserPreference, alias="userPreferences")
    last_series_context: Optional[List[int]] = Field(default_factory=list, alias="lastSeriesContext")

    class Config:
        """Pydantic config."""

        populate_by_name = True


# API Request/Response models
class ChatRequest(BaseModel):
    """Chat request model."""

    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    """Chat response model."""

    message: str
    session_id: str