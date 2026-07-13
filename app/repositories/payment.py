from datetime import UTC
from decimal import Decimal
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import selectinload

from app.models import Order, OrderStatus, Payment, PaymentStatus, User, UserGroupEnum


class PaymentRepository:
    def __init__(self, session):
        self._session = session

    async def get_payments_by_order_id(self, order_id: int) -> list[Payment] | []:
        return (
            await self._session.scalars(
                select(Payment.id)
                .join(Payment.order)
                .where(
                    Payment.order_id == order_id,
                    or_(
                        Order.status == OrderStatus.PENDING,
                        Order.status == OrderStatus.PAID,
                    ),
                )
            )
        ).all()

    async def create_payment(
        self, user_id: int, order_id: int, calculated_total: int | float
    ) -> Payment:
        new_payment = Payment(
            user_id=user_id,
            order_id=order_id,
            amount=Decimal(calculated_total),
            status=PaymentStatus.PENDING,
            payment_items=[],
        )
        self._session.add(new_payment)
        await self._session.flush()
        return new_payment

    async def get_payment_by_id(self, payment_id: int) -> Payment | None:
        return await self._session.scalar(
            select(Payment)
            .options(selectinload(Payment.payment_items))
            .where(Payment.id == payment_id)
        )

    async def get_payment_by_external_id(
        self, payment_external_id: int
    ) -> Payment | None:
        return await self._session.scalar(
            select(Payment).where(Payment.external_payment_id == payment_external_id)
        )

    async def get_filtered_payments(
        self, current_user: User, filters: dict[str, Any]
    ) -> list[Payment]:
        query = (
            select(Payment)
            .options(selectinload(Payment.payment_items))
            .order_by(Payment.created_at.desc())
        )
        if current_user.group.name != UserGroupEnum.ADMIN:
            query = query.where(Payment.user_id == current_user.id)
        else:
            if filters.get("user_id"):
                query = query.where(Payment.user_id == filters["user_id"])
            if filters.get("status"):
                query = query.where(Payment.status == filters["status"])
        if filters.get("start_date"):
            start_date = filters["start_date"]
            if start_date.tzinfo is None:
                start_date = start_date.replace(tzinfo=UTC)
            else:
                start_date = start_date.astimezone(UTC)
            query = query.where(Payment.created_at >= start_date)
        if filters.get("end_date"):
            end_date = filters["end_date"]
            if end_date.tzinfo is None:
                end_date = end_date.replace(tzinfo=UTC)
            else:
                end_date = end_date.astimezone(UTC)
            query = query.where(Payment.created_at <= end_date)
        result = await self._session.execute(query)
        return list(result.scalars().all())
