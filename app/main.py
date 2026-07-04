from fastapi import FastAPI

from app.api.health import router as health_router
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    debug=settings.app_debug,
    version="0.1.0",
)

register_exception_handlers(app)
app.include_router(health_router)


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "Welcome to Online Cinema API"}
