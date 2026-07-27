from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.movie import MovieBase


class PurchasedMoviesResponse(BaseModel):
    id: int
    movie: MovieBase
    purchase_at: datetime

    model_config = ConfigDict(from_attributes=True)
