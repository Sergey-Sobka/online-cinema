from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.exceptions import register_exception_handlers
from app.main import app


def test_missing_route_uses_error_response_format() -> None:
    client = TestClient(app)

    response = client.get("/missing")

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "HTTP_404",
            "message": "Not Found",
            "details": [],
        }
    }


def test_validation_error_uses_error_response_format() -> None:
    test_app = FastAPI()
    register_exception_handlers(test_app)

    @test_app.get("/items")
    async def read_items(limit: int) -> dict[str, int]:
        return {"limit": limit}

    client = TestClient(test_app)

    response = client.get("/items", params={"limit": "invalid"})

    assert response.status_code == 422
    payload = response.json()
    assert payload["error"]["code"] == "VALIDATION_ERROR"
    assert payload["error"]["message"] == "Request validation failed."
    assert payload["error"]["details"][0]["loc"] == ["query", "limit"]
    assert payload["error"]["details"][0]["type"] == "int_parsing"
