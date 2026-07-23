from unittest.mock import patch

import pytest
from fastapi import status

from tests.test_movies.mocks import MOCK_FULL_MOVIE


@pytest.mark.asyncio
class TestUserSocialActions:
    @patch("app.services.movies.MovieService.get_movies_catalog")
    async def test_get_user_favorites(self, mock_service, client):
        mock_service.return_value = (1, [MOCK_FULL_MOVIE])
        response = await client.get("/api/v1/movies/user/favorites")
        assert response.status_code == status.HTTP_200_OK

    @patch("app.services.movies.MovieService.get_movies_catalog")
    async def test_get_user_favorites_rejects_invalid_sorting(
        self, mock_service, client
    ):
        response = await client.get("/api/v1/movies/user/favorites?sort_by=name")

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        mock_service.assert_not_called()

    @patch("app.services.social.SocialService.add_favorite")
    async def test_add_favorite(self, mock_service, client):
        mock_service.return_value = None
        response = await client.post("/api/v1/movies/10/favorite")
        assert response.status_code == status.HTTP_204_NO_CONTENT

    @patch("app.services.social.SocialService.like_movie")
    async def test_like_movie(self, mock_service, client):
        mock_service.return_value = None
        response = await client.post("/api/v1/movies/10/like?is_like=true")
        assert response.status_code == status.HTTP_204_NO_CONTENT

    @patch("app.services.social.SocialService.add_comment")
    async def test_add_comment(self, mock_service, client):
        mock_service.return_value = {
            "id": 1,
            "text": "Awesome!",
            "movie_id": 10,
            "user_id": 42,
            "parent_id": None,
        }
        response = await client.post(
            "/api/v1/movies/10/comments", json={"text": "Awesome!"}
        )
        assert response.status_code == status.HTTP_201_CREATED

    @patch("app.services.social.SocialService.like_comment")
    async def test_like_comment(self, mock_service, client):
        mock_service.return_value = None
        response = await client.post("/api/v1/movies/comments/1/like?is_like=true")
        assert response.status_code == status.HTTP_204_NO_CONTENT
