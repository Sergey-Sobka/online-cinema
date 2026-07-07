from unittest.mock import patch

import pytest
from fastapi import status

from tests.test_movies.mocks import MOCK_FULL_MOVIE


@pytest.mark.asyncio
class TestUserSocialActions:
    @patch("app.crud.movies.get_movies_catalog")
    async def test_get_user_favorites(self, mock_crud, client):
        mock_crud.return_value = (1, [MOCK_FULL_MOVIE])
        response = await client.get("/api/v1/movies/user/favorites")
        assert response.status_code == status.HTTP_200_OK

    @patch("app.crud.social.toggle_favorite")
    async def test_add_favorite(self, mock_social, client):
        response = await client.post("/api/v1/movies/10/favorite")
        assert response.status_code == status.HTTP_204_NO_CONTENT

    @patch("app.api.social.send_comment_notification_task.delay")
    @patch("app.crud.social.set_movie_like")
    async def test_like_movie(self, mock_social, mock_notification, client):
        response = await client.post("/api/v1/movies/10/like?is_like=true")
        assert response.status_code == status.HTTP_204_NO_CONTENT

    @patch("app.crud.social.add_movie_comment")
    async def test_add_comment(self, mock_social, client):
        mock_social.return_value = {
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
