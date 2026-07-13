from app.core.uow_abstraction import IUnitOfWork
from app.repositories.order import OrderRepository
from app.repositories.payment import PaymentRepository
from app.repositories.users import UserRepository


class SqlAlchemyUnitOfWork(IUnitOfWork):
    def __init__(self, session_factory):
        self.session_factory = session_factory
        self._repositories = {}

    async def __aenter__(self):
        self.session = self.session_factory()
        return self

    async def commit(self):
        await self.session.commit()

    async def rollback(self):
        await self.session.rollback()

    def get_repo(self, repo_class):
        if not hasattr(self, "session"):
            self.session = self.session_factory()

        if repo_class not in self._repositories:
            self._repositories[repo_class] = repo_class(self.session)
        return self._repositories[repo_class]

    @property
    def orders(self):
        return self.get_repo(OrderRepository)

    @property
    def payments(self):
        return self.get_repo(PaymentRepository)

    @property
    def users(self):
        return self.get_repo(UserRepository)

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            await self.rollback()
        else:
            await self.commit()
        await self.session.close()
