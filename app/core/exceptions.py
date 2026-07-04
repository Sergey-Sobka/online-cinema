from http import HTTPStatus
from typing import Any, cast

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


def build_error_response(
    code: str,
    message: str,
    details: list[dict[str, Any]] | None = None,
) -> dict[str, dict[str, Any]]:
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details or [],
        }
    }


async def http_exception_handler(
    _request: Request,
    exc: Exception,
) -> JSONResponse:
    http_exc = cast(StarletteHTTPException, exc)

    detail = http_exc.detail
    message = (
        detail if isinstance(detail, str) else HTTPStatus(http_exc.status_code).phrase
    )

    return JSONResponse(
        status_code=http_exc.status_code,
        content=jsonable_encoder(
            build_error_response(
                code=f"HTTP_{http_exc.status_code}",
                message=message,
            )
        ),
        headers=http_exc.headers,
    )


async def validation_exception_handler(
    _request: Request,
    exc: Exception,
) -> JSONResponse:
    validation_exc = cast(RequestValidationError, exc)

    details = [
        {
            "loc": list(error.get("loc", ())),
            "message": error.get("msg", ""),
            "type": error.get("type", ""),
        }
        for error in validation_exc.errors()
    ]

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder(
            build_error_response(
                code="VALIDATION_ERROR",
                message="Request validation failed.",
                details=details,
            )
        ),
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
