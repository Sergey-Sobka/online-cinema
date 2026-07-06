import uuid
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class GenreSchema(BaseModel):
    id: int
    name: str
    model_config = ConfigDict(from_attributes=True)


class StarSchema(BaseModel):
    id: int
    name: str
    model_config = ConfigDict(from_attributes=True)


class DirectorSchema(BaseModel):
    id: int
    name: str
    model_config = ConfigDict(from_attributes=True)


class CertificationSchema(BaseModel):
    id: int
    name: str
    model_config = ConfigDict(from_attributes=True)


class MovieBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    year: int = Field(..., description="Year of release")
    time: int = Field(..., ge=1, description="time in minutes")
    imdb: float = Field(..., ge=0.0, le=10.0, description="Rating on IMDB")
    votes: int = Field(default=0, ge=0)
    meta_score: float | None = Field(None, ge=0.0, le=100.0)
    gross: float | None = Field(None, ge=0.0)
    description: str = Field(..., min_length=5)
    price: Decimal = Field(..., max_digits=10, decimal_places=2)
    certification_id: int

    @field_validator("year")
    @classmethod
    def validate_year(cls, v: int) -> int:
        if v < 1888 or v > 2030:
            raise ValueError("Year must be between 1888 and 2030")
        return v


class MovieCreate(MovieBase):
    genre_ids: list[int] = Field(default=[])
    director_ids: list[int] = Field(default=[])
    star_ids: list[int] = Field(default=[])


class MovieUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    year: int | None = None
    time: int | None = Field(None, ge=1)
    imdb: float | None = Field(None, ge=0.0, le=10.0)
    votes: int | None = Field(None, ge=0)
    meta_score: float | None = Field(None, ge=0.0, le=100.0)
    gross: float | None = None
    description: str | None = None
    price: Decimal | None = Field(None, max_digits=10, decimal_places=2)
    certification_id: int | None = None
    genre_ids: list[int] | None = None
    director_ids: list[int] | None = None
    star_ids: list[int] | None = None


class MovieResponse(MovieBase):
    id: int
    uuid: uuid.UUID
    genres: list[GenreSchema]
    directors: list[DirectorSchema]
    stars: list[StarSchema]
    certification: CertificationSchema

    model_config = ConfigDict(from_attributes=True)


class PaginatedMovieResponse(BaseModel):
    total: int
    page: int
    limit: int
    results: list[MovieResponse]
    model_config = ConfigDict(from_attributes=True)


class GenreWithCountResponse(GenreSchema):
    movies_count: int


class CommentCreate(BaseModel):
    text: str = Field(..., min_length=1, max_length=1000)
    parent_id: int | None = Field(None)


class CommentResponse(BaseModel):
    id: int
    user_id: int
    movie_id: int
    text: str
    parent_id: int | None

    model_config = ConfigDict(from_attributes=True)
