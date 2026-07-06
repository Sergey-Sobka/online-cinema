from decimal import Decimal
from uuid import UUID as PyUUID
from uuid import uuid4

from sqlalchemy import UUID, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class MovieGenre(Base):
    __tablename__ = "movie_genres"
    movie_id: Mapped[int] = mapped_column(
        ForeignKey("movies.id", ondelete="CASCADE"), primary_key=True
    )
    genre_id: Mapped[int] = mapped_column(
        ForeignKey("genres.id", ondelete="CASCADE"), primary_key=True
    )


class MovieDirector(Base):
    __tablename__ = "movie_directors"
    movie_id: Mapped[int] = mapped_column(
        ForeignKey("movies.id", ondelete="CASCADE"), primary_key=True
    )
    director_id: Mapped[int] = mapped_column(
        ForeignKey("directors.id", ondelete="CASCADE"), primary_key=True
    )


class MovieStar(Base):
    __tablename__ = "movie_stars"
    movie_id: Mapped[int] = mapped_column(
        ForeignKey("movies.id", ondelete="CASCADE"), primary_key=True
    )
    star_id: Mapped[int] = mapped_column(
        ForeignKey("stars.id", ondelete="CASCADE"), primary_key=True
    )


class Genre(Base):
    __tablename__ = "genres"
    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

    movies: Mapped[list["Movie"]] = relationship(
        secondary="movie_genres", back_populates="genres"
    )


class Director(Base):
    __tablename__ = "directors"
    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    movies: Mapped[list["Movie"]] = relationship(
        secondary="movie_directors", back_populates="directors"
    )


class Star(Base):
    __tablename__ = "stars"
    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    movies: Mapped[list["Movie"]] = relationship(
        secondary="movie_stars", back_populates="stars"
    )


class Certification(Base):
    __tablename__ = "certifications"
    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

    movies: Mapped[list["Movie"]] = relationship(back_populates="certification")


class Movie(Base):
    __tablename__ = "movies"
    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    uuid: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), default=uuid4, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    year: Mapped[int] = mapped_column(nullable=False)
    time: Mapped[int] = mapped_column(nullable=False)
    imdb: Mapped[float] = mapped_column(nullable=False)
    votes: Mapped[int] = mapped_column(nullable=False)
    meta_score: Mapped[float | None] = mapped_column(nullable=True)
    gross: Mapped[float | None] = mapped_column(nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    certification_id: Mapped[int] = mapped_column(
        ForeignKey("certifications.id"), nullable=False
    )

    certification: Mapped["Certification"] = relationship(back_populates="movies")
    genres: Mapped[list["Genre"]] = relationship(
        secondary="movie_genres", back_populates="movies"
    )
    directors: Mapped[list["Director"]] = relationship(
        secondary="movie_directors", back_populates="movies"
    )
    stars: Mapped[list["Star"]] = relationship(
        secondary="movie_stars", back_populates="movies"
    )

    __table_args__ = (
        UniqueConstraint("name", "year", "time", name="uq_movie_name_year_time"),
    )
