from datetime import datetime

from sqlalchemy import ForeignKey, DateTime, func, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class PurchasedMovie(Base):
    __tablename__ = "purchased_movies"

    id : Mapped[int] = mapped_column(primary_key=True)
    user_id : Mapped[int] = mapped_column(ForeignKey("users.id"), ondelete="CASCADE")
    movie_id : Mapped[int] = mapped_column(ForeignKey("movies.id"), ondelete="CASCADE")
    purchase_at : Mapped[datetime] = mapped_column(DateTime(timezone=True),
                                                   server_default=func.now(),
                                                   nullable=False)
    movie = relationship("Movie")
    __table_args__ = (
        UniqueConstraint("user_id", "movie_id", name="uq_user_movie"),
    )