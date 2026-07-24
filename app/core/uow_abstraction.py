from abc import ABC, abstractmethod
from typing import Any


class IUnitOfWork(ABC):
    session: Any
    orders: Any
    payments: Any
    users: Any
    purchased_movies: Any

    @abstractmethod
    async def commit(self) -> None:
        pass

    @abstractmethod
    async def rollback(self) -> None:
        pass

    @abstractmethod
    async def __aenter__(self) -> "IUnitOfWork": ...

    @abstractmethod
    async def __aexit__(self, *args: Any) -> None: ...
