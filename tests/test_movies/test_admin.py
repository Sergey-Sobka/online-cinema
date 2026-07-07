from unittest.mock import patch

import pytest
from fastapi import status

from tests.test_movies.mocks import MOCK_FULL_MOVIE


@pytest.mark.asyncio
class TestAdminMovieManagement:
    @patch("app.crud.movies.create_movie")
    async def test_create_new_movie(self, mock_crud, client):
        payload = {
            "title": "The Matrix",
            "name": "The Matrix",
            "description": "Neo...",
            "year": 1999,
            "time": 136,
            "imdb": 8.7,
            "price": 9.99,
            "certification_id": 1,
        }
        mock_crud.return_value = MOCK_FULL_MOVIE

        response = await client.post("/api/v1/admin/movies", json=payload)
        assert response.status_code == status.HTTP_201_CREATED

    @patch("app.crud.movies.update_movie")
    async def test_update_existing_movie_success(self, mock_crud, client):
        mock_crud.return_value = MOCK_FULL_MOVIE

        response = await client.put(
            "/api/v1/admin/movies/1", json={"title": "The Matrix Reloaded"}
        )
        assert response.status_code == status.HTTP_200_OK

    @patch("app.crud.movies.delete_movie")
    async def test_delete_existing_movie_success(self, mock_crud, client):
        mock_crud.return_value = True
        response = await client.delete("/api/v1/admin/movies/1")
        assert response.status_code == status.HTTP_204_NO_CONTENT
