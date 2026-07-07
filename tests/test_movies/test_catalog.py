from unittest.mock import patch

import pytest
from fastapi import status

from tests.test_movies.mocks import MOCK_FULL_MOVIE


@pytest.mark.asyncio
class TestMovieCatalog:
    @patch("app.crud.movies.get_movies_catalog")
    async def test_get_movies_success(self, mock_crud, client):
        mock_crud.return_value = (1, [MOCK_FULL_MOVIE])
        response = await client.get("/api/v1/movies?page=1&limit=10&sort_by=popularity")
        assert response.status_code == status.HTTP_200_OK

    @patch("app.crud.movies.get_genres_with_counts")
    async def test_get_genres_list(self, mock_crud, client):
        mock_crud.return_value = [{"id": 1, "name": "Sci-Fi", "movies_count": 5}]
        response = await client.get("/api/v1/movies/genres")
        assert response.status_code == status.HTTP_200_OK

    @patch("app.crud.movies.get_movie_by_id")
    async def test_get_movie_detail_success(self, mock_crud, client):
        mock_crud.return_value = MOCK_FULL_MOVIE
        response = await client.get("/api/v1/movies/123")
        assert response.status_code == status.HTTP_200_OK

    @patch("app.crud.movies.get_movie_by_id")
    async def test_get_movie_detail_404(self, mock_crud, client):
        mock_crud.return_value = None
        response = await client.get("/api/v1/movies/999")
        assert response.status_code == status.HTTP_404_NOT_FOUND
