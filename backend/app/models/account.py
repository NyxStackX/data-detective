from datetime import date

from sqlalchemy import Date, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database.base import Base


class Account(Base):
    __tablename__ = "accounts"

    account_id: Mapped[str] = mapped_column(
        String(50),
        primary_key=True,
    )

    entity_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("entities.entity_id"),
        nullable=False,
    )

    bank_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    country: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    city: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    currency: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )

    account_type: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    opening_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    closing_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    status: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
