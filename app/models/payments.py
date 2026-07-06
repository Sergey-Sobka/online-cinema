import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Enum, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class PaymentStatus(str, enum.Enum):
    SUCCESSFUL = "successful"
    CANCELED = "canceled"
    REFUNDED = "refunded"
    PENDING = "pending"


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    user = relationship("User")
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
    )
    order: Mapped["Order"] = relationship(back_populates="payments")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus),
        default=PaymentStatus.PENDING,
        nullable=False,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    external_payment_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    payment_items: Mapped[list["PaymentItems"]] = relationship(
        back_populates="payment", cascade="all, delete-orphan"
    )


class PaymentItems(Base):
    __tablename__ = "payments_items"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    payment_id: Mapped[int] = mapped_column(
        ForeignKey("payments.id", ondelete="CASCADE"),
        nullable=False,
    )
    payment: Mapped["Payment"] = relationship(back_populates="payment_items")
    order_item_id: Mapped[int] = mapped_column(
        ForeignKey("order_items.id", ondelete="CASCADE"),
        nullable=False,
    )
    order_item: Mapped["OrderItem"] = relationship(back_populates="payment_items")
    price_at_payment: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
