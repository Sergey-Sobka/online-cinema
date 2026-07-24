from datetime import datetime
from typing import List

from pydantic import BaseModel, ConfigDict

from app.schemas.movie import MovieBase


class PurchasedMoviesResponse(BaseModel):
    id: int
    movie: MovieBase
    purchased_at: datetime


    model_config = ConfigDict(from_attributes=True)