from pydantic import BaseModel, ConfigDict

from app.schemas.movie import MovieResponse


class CartItemRead(BaseModel):
    id: int
    cart_id: int
    movie: MovieResponse

    model_config = ConfigDict(from_attributes=True)


class CartRead(BaseModel):
    id: int
    user_id: int
    cart_items: list[CartItemRead]

    model_config = ConfigDict(from_attributes=True)
