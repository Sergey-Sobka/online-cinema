from typing import Any

from app.core.uow_abstraction import IUnitOfWork
from app.repositories.order import OrderRepository
from app.repositories.payment import PaymentRepository
from app.repositories.users import UserRepository


class SqlAlchemyUnitOfWork(IUnitOfWork):
    def __init__(self, session_factory: Any) -> None:
        self.session_factory = session_factory
        self._repositories = {}

    async def __aenter__(self) -> IUnitOfWork:
        self.session = self.session_factory()
        return self

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()

    def get_repo(self, repo_class: Any) -> Any:
        if not hasattr(self, "session"):
            self.session = self.session_factory()

        if repo_class not in self._repositories:
            self._repositories[repo_class] = repo_class(self.session)
        return self._repositories[repo_class]

    @property
    def orders(self) -> OrderRepository:
        return self.get_repo(OrderRepository)

    @property
    def payments(self) -> PaymentRepository:
        return self.get_repo(PaymentRepository)

    @property
    def users(self) -> UserRepository:
        return self.get_repo(UserRepository)

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if exc_type:
            await self.rollback()
        else:
            await self.commit()
        await self.session.close()
