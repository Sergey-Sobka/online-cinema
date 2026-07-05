import enum
from decimal import Decimal
from typing import List
from sqlalchemy import ForeignKey, String, Numeric, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

# class User(Base):
#     __tablename__ = "users"
#
#     id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
#     email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
#     role: Mapped[str] = mapped_column(String(50), default="user", nullable=False)  # user / admin / moderator
#     orders: Mapped[List["Order"]] = relationship(back_populates="user")
#     payments: Mapped[List["Payment"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class OrderStatus(enum.Enum):
    CANCELED = "canceled"
    PAID = "paid"
    PENDING = "pending"


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus),
        default=OrderStatus.PENDING,
        nullable=False,
    )
    user = relationship("User")
    order_items: Mapped[List["OrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )
    payments: Mapped[List["Payment"]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False)
    movie_id: Mapped[int] = mapped_column(nullable=False)
    price_at_order: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    order: Mapped["Order"] = relationship(back_populates="order_items")
    payment_items: Mapped[List["PaymentItems"]] = relationship(
        back_populates="order_item", cascade="all, delete-orphan"
    )
