import uuid

import pytest
from pydantic import ValidationError

from app.schemas.cart import CartItemRead, CartRead
from app.schemas.movie import MovieResponse


class FakeORM:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


@pytest.fixture
def valid_movie_data():
    return {
        "id": 1,
        "uuid": str(uuid.uuid4()),
        "name": "Inception",
        "year": 2010,
        "time": 148,
        "imdb": 8.8,
        "description": "A thief who steals corporate secrets...",
        "price": 299,
        "certification_id": 1,
        "genres": [{"id": 1, "name": "Sci-Fi"}, {"id": 2, "name": "Action"}],
        "directors": [{"id": 1, "name": "Christopher Nolan"}],
        "stars": [
            {"id": 1, "name": "Leonardo DiCaprio"},
            {"id": 2, "name": "Joseph Gordon-Levitt"},
        ],
        "certification": {"id": 1, "name": "PG-13"},
    }


@pytest.fixture
def valid_cart_item_data(valid_movie_data):
    return {"id": 10, "cart_id": 100, "movie": MovieResponse(**valid_movie_data)}


class TestCartSchemas:
    def test_cart_item_read_from_dict(self, valid_cart_item_data):
        item = CartItemRead(**valid_cart_item_data)

        assert item.id == 10
        assert item.cart_id == 100
        assert item.movie.id == 1

    def test_cart_read_from_dict(self, valid_cart_item_data):
        cart_data = {"id": 100, "user_id": 42, "cart_items": [valid_cart_item_data]}
        cart = CartRead(**cart_data)

        assert cart.id == 100
        assert cart.user_id == 42
        assert len(cart.cart_items) == 1
        assert cart.cart_items[0].id == 10

    def test_cart_read_from_attributes(self, valid_movie_data):
        movie_data = valid_movie_data.copy()
        movie_data["genres"] = [FakeORM(**g) for g in movie_data["genres"]]
        movie_data["directors"] = [FakeORM(**d) for d in movie_data["directors"]]
        movie_data["stars"] = [FakeORM(**s) for s in movie_data["stars"]]
        movie_data["certification"] = FakeORM(**movie_data["certification"])

        fake_movie_orm = FakeORM(**movie_data)
        fake_item_orm = FakeORM(id=15, cart_id=200, movie=fake_movie_orm)
        fake_cart_orm = FakeORM(id=200, user_id=77, cart_items=[fake_item_orm])

        cart = CartRead.model_validate(fake_cart_orm)

        assert cart.id == 200
        assert cart.user_id == 77
        assert len(cart.cart_items) == 1
        assert cart.cart_items[0].movie.name == "Inception"

    def test_cart_item_invalid_types(self):
        invalid_data = {
            "id": "not-an-int",
            "cart_id": 100,
            "movie": {
                "id": 1,
                "name": "Inception",
            },
        }

        with pytest.raises(ValidationError) as exc_info:
            CartItemRead(**invalid_data)

        assert "id" in str(exc_info.value)

    def test_cart_read_missing_required_fields(self):
        incomplete_data = {"id": 1}

        with pytest.raises(ValidationError) as exc_info:
            CartRead(**incomplete_data)

        assert "user_id" in str(exc_info.value)
        assert "cart_items" in str(exc_info.value)
