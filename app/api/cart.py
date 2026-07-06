from api.dependencies import get_current_user
from db.session import get_db_session
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud, services
from app.models import User
from app.schemas.cart import CartItemRead, CartRead
from models import Cart, CartItem

router = APIRouter(prefix="/cart", tags=["Cart"])


@router.get("/", response_model=CartRead)
async def view_cart(
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> Cart:
    cart = await crud.cart.get_cart_by_user_id(db, user_id=current_user.id)
    if not cart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cart is not found"
        )
    return cart


@router.post("/items", response_model=CartItemRead, status_code=status.HTTP_201_CREATED)
async def add_movie_to_cart(
    movie_id: int,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> CartItem:
    return await services.cart.add_movie_to_cart(
        db=db, user_id=current_user.id, movie_id=movie_id
    )


@router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_item_from_cart(
    item_id: int,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> None:
    cart = await crud.cart.get_cart_by_user_id(db, user_id=current_user.id)

    if not cart:
        raise HTTPException(status_code=404, detail="Cart is not found")

    user_item_ids = [item.id for item in cart.cart_items]

    if item_id not in user_item_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie is not in the cart",
        )

    await crud.cart.delete_item_from_cart(db, item_id=item_id)

    return None


@router.delete("/", status_code=status.HTTP_204_NO_CONTENT)
async def clear_cart(
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> None:
    cart = await crud.cart.get_cart_by_user_id(db, user_id=current_user.id)
    if not cart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cart is not found"
        )

    await crud.cart.clear_cart(db, cart_id=cart.id)

    return None
