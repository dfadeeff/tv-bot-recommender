"""Data models for the TV Series Recommender."""

from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field, validator


class Translation(BaseModel):
    """Translation model."""

    language: str
    value: str


class Status(BaseModel):
    """Status model for series/movies."""

    id: int
    name: str
    record_type: Optional[str] = Field(None, alias="recordType")
    keep_updated: Optional[bool] = Field(None, alias="keepUpdated")


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
    series_id: Optional[int] = Field(None, alias="seriesId")
    movie_id: Optional[int] = Field(None, alias="movieId")
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
    type: Optional[Dict[str, Any]] = None
    episodes: Optional[List[Dict[str, Any]]] = None

    class Config:
        """Pydantic config."""
        populate_by_name = True


class Episode(BaseModel):
    """Episode model."""

    id: int
    series_id: int = Field(..., alias="seriesId")
    season_id: Optional[int] = Field(None, alias="seasonId")
    name: str
    aired: Optional[str] = None
    runtime: Optional[int] = None
    overview: Optional[str] = None
    season_number: Optional[int] = Field(None, alias="seasonNumber")
    episode_number: Optional[int] = Field(None, alias="number")
    image_url: Optional[str] = Field(None, alias="imageUrl")
    name_translations: Optional[List[str]] = Field(None, alias="nameTranslations")
    overview_translations: Optional[List[str]] = Field(None, alias="overviewTranslations")

    class Config:
        """Pydantic config."""
        populate_by_name = True


class Award(BaseModel):
    """Award model."""

    id: int
    name: str
    categories: Optional[List[Dict[str, Any]]] = None

    class Config:
        """Pydantic config."""
        populate_by_name = True


class AwardCategory(BaseModel):
    """Award category model."""

    id: int
    name: str
    award_id: int = Field(..., alias="awardId")
    allowed_types: List[str] = Field([], alias="allowedTypes")

    class Config:
        """Pydantic config."""
        populate_by_name = True


class AwardRecord(BaseModel):
    """Award record model."""

    id: int
    category_id: int = Field(..., alias="categoryId")
    name: Optional[str] = None
    year: Optional[str] = None
    nominee: Optional[str] = None
    series_id: Optional[int] = Field(None, alias="seriesId")
    movie_id: Optional[int] = Field(None, alias="movieId")
    episode_id: Optional[int] = Field(None, alias="episodeId")
    person_id: Optional[int] = Field(None, alias="personId")
    is_winner: Optional[bool] = Field(None, alias="isWinner")

    class Config:
        """Pydantic config."""
        populate_by_name = True


class MovieBase(BaseModel):
    """Base movie model."""

    id: int
    name: str
    slug: str
    aliases: Optional[List[str]] = None
    image: Optional[str] = None
    last_updated: Optional[str] = Field(None, alias="lastUpdated")
    name_translations: Optional[List[str]] = Field(None, alias="nameTranslations")
    overview_translations: Optional[List[str]] = Field(None, alias="overviewTranslations")
    score: Optional[float] = None
    status: Optional[Status] = None
    runtime: Optional[int] = None
    year: Optional[str] = None

    class Config:
        """Pydantic config."""
        populate_by_name = True


class SeriesBase(BaseModel):
    """Base TV Series model."""

    id: int
    name: str
    slug: str
    aliases: Optional[List[str]] = None
    image: Optional[str] = None
    # Allow status to be either a string or a Status object
    status: Optional[Union[str, Status]] = None
    original_network: Optional[Network] = Field(None, alias="originalNetwork")
    overview: Optional[str] = None
    first_aired: Optional[str] = Field(None, alias="firstAired")
    last_aired: Optional[str] = Field(None, alias="lastAired")
    score: Optional[float] = None
    name_translations: Optional[List[str]] = Field(None, alias="nameTranslations")
    overview_translations: Optional[List[str]] = Field(None, alias="overviewTranslations")

    class Config:
        """Pydantic config."""
        populate_by_name = True

    # Add a validator to handle string status values
    @validator('status', pre=True)
    def validate_status(cls, v):
        if isinstance(v, str):
            # Create a simple Status object from string
            return {"id": 0, "name": v}
        return v


class Series(SeriesBase):
    """Extended TV Series model."""

    genres: Optional[List[Genre]] = None
    seasons: Optional[List[Season]] = None
    characters: Optional[List[Character]] = None
    awards: Optional[List[Dict[str, Any]]] = None

    class Config:
        """Pydantic config."""
        populate_by_name = True


class PeopleBase(BaseModel):
    """Base People model."""

    id: int
    name: str
    aliases: Optional[List[str]] = None
    image: Optional[str] = None
    name_translations: Optional[List[str]] = Field(None, alias="nameTranslations")
    overview_translations: Optional[List[str]] = Field(None, alias="overviewTranslations")
    score: Optional[float] = None

    class Config:
        """Pydantic config."""
        populate_by_name = True


class Company(BaseModel):
    """Company model."""

    id: int
    name: str
    slug: str
    aliases: Optional[List[str]] = None
    name_translations: Optional[List[str]] = Field(None, alias="nameTranslations")
    primary_type: Optional[int] = Field(None, alias="primaryType")
    country: Optional[str] = None

    class Config:
        """Pydantic config."""
        populate_by_name = True


class SearchResult(BaseModel):
    """Search result model."""

    object_id: str = Field(..., alias="objectID")
    type: str
    name: str
    image_url: Optional[str] = Field(None, alias="image_url")
    first_aired: Optional[str] = Field(None, alias="first_air_time")
    overview: Optional[str] = None
    aliases: Optional[List[str]] = None
    country: Optional[str] = None
    network: Optional[str] = None
    year: Optional[str] = None
    tvdb_id: Optional[int] = Field(None, alias="tvdb_id")
    imdb_id: Optional[str] = Field(None, alias="imdb_id")

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
