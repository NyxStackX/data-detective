from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.database.dependencies import get_db
from backend.app.models.transaction import Transaction


router = APIRouter(prefix="/transactions", tags=["Transactions"])


@router.get("")
def get_transactions(
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    transaction_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    query = select(Transaction)

    if transaction_type:
        query = query.where(
            Transaction.transaction_type.ilike(transaction_type)
        )

    if status:
        query = query.where(
            Transaction.status.ilike(status)
        )

    query = query.order_by(Transaction.transaction_date)

    total = len(db.execute(query).scalars().all())

    transactions = (
        db.execute(
            query.offset(offset).limit(limit)
        )
        .scalars()
        .all()
    )

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "transactions": [
            {
                "transaction_id": transaction.transaction_id,
                "transaction_date": transaction.transaction_date.isoformat(),
                "source_account_id": transaction.source_account_id,
                "destination_account_id": transaction.destination_account_id,
                "source_entity_id": transaction.source_entity_id,
                "destination_entity_id": transaction.destination_entity_id,
                "amount": float(transaction.amount),
                "currency": transaction.currency,
                "amount_eur": (
                    float(transaction.amount_eur)
                    if transaction.amount_eur is not None
                    else None
                ),
                "transaction_type": transaction.transaction_type,
                "reference": transaction.reference,
                "description": transaction.description,
                "status": transaction.status,
                "authorized_by": transaction.authorized_by,
                "created_by": transaction.created_by,
            }
            for transaction in transactions
        ],
    }
