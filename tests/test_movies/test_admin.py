from unittest.mock import patch

import pytest
from fastapi import status

from tests.test_movies.mocks import MOCK_FULL_MOVIE


@pytest.mark.asyncio
class TestAdminMovieManagement:
    @patch("app.services.movies.MovieService.create_new_movie")
    async def test_create_new_movie(self, mock_service, client):
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
        mock_service.return_value = MOCK_FULL_MOVIE

        response = await client.post("/api/v1/admin/movies", json=payload)
        assert response.status_code == status.HTTP_201_CREATED

    @patch("app.services.movies.MovieService.update_existing_movie")
    async def test_update_existing_movie_success(self, mock_service, client):
        mock_service.return_value = MOCK_FULL_MOVIE

        response = await client.put(
            "/api/v1/admin/movies/1", json={"title": "The Matrix Reloaded"}
        )
        assert response.status_code == status.HTTP_200_OK

    @patch("app.services.movies.MovieService.delete_existing_movie")
    async def test_delete_existing_movie_success(self, mock_service, client):
        mock_service.return_value = None
        response = await client.delete("/api/v1/admin/movies/1")
        assert response.status_code == status.HTTP_204_NO_CONTENT
