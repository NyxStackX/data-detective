from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database.base import Base


class Transaction(Base):
    __tablename__ = "transactions"

    transaction_id: Mapped[str] = mapped_column(
        String(50),
        primary_key=True,
    )

    transaction_date: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
    )

    source_account_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("accounts.account_id"),
        nullable=False,
    )

    destination_account_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("accounts.account_id"),
        nullable=False,
    )

    source_entity_id: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    destination_entity_id: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
    )

    currency: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )

    amount_eur: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 2),
        nullable=True,
    )

    transaction_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    reference: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    authorized_by: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    created_by: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
