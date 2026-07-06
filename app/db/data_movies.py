import asyncio
import uuid
from decimal import Decimal

from app.db.session import AsyncSessionLocal
from app.models.movie import Certification, Director, Genre, Movie, Star


async def seed_data() -> None:
    print("Starting database seeding with sample movie data...")

    async with AsyncSessionLocal() as session:
        cert_pg13 = Certification(name="PG-13")
        cert_r = Certification(name="R")
        session.add_all([cert_pg13, cert_r])
        await session.flush()

        action = Genre(name="Action")
        drama = Genre(name="Drama")
        sci_fi = Genre(name="Sci-Fi")
        thriller = Genre(name="Thriller")
        session.add_all([action, drama, sci_fi, thriller])
        await session.flush()

        keanu = Star(name="Keanu Reeves")
        dicaprio = Star(name="Leonardo DiCaprio")
        bale = Star(name="Christian Bale")
        session.add_all([keanu, dicaprio, bale])
        await session.flush()

        nolan = Director(name="Christopher Nolan")
        wachowskis = Director(name="Lana Wachowski")
        session.add_all([nolan, wachowskis])
        await session.flush()

        movie1 = Movie(
            uuid=uuid.uuid4(),
            name="Inception",
            year=2010,
            time=148,
            imdb=8.8,
            votes=2500000,
            meta_score=74.0,
            gross=292576195.0,
            description="A thief who steals corporate "
                        "secrets through the use of dream-sharing technology.",
            price=Decimal("14.99"),
            certification_id=cert_pg13.id,
            genres=[action, sci_fi, thriller],
            directors=[nolan],
            stars=[dicaprio],
        )

        movie2 = Movie(
            uuid=uuid.uuid4(),
            name="The Matrix",
            year=1999,
            time=136,
            imdb=8.7,
            votes=1900000,
            meta_score=73.0,
            gross=171479902.0,
            description="When a beautiful stranger "
                        "leads computer hacker Neo to a forbidding underworld...",
            price=Decimal("9.99"),
            certification_id=cert_r.id,
            genres=[action, sci_fi],
            directors=[wachowskis],
            stars=[keanu],
        )

        movie3 = Movie(
            uuid=uuid.uuid4(),
            name="The Dark Knight",
            year=2008,
            time=152,
            imdb=9.0,
            votes=2800000,
            meta_score=84.0,
            gross=534858444.0,
            description="When the menace known as "
                        "the Joker wreaks havoc and chaos on the people of Gotham...",
            price=Decimal("19.99"),
            certification_id=cert_pg13.id,
            genres=[action, drama, thriller],
            directors=[nolan],
            stars=[bale],
        )

        session.add_all([movie1, movie2, movie3])
        await session.commit()

    print("Database successfully seeded with movies, genres, stars, and directors!")


if __name__ == "__main__":
    asyncio.run(seed_data())
