from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.database.dependencies import get_db
from backend.app.models.account import Account
from backend.app.models.entity import Entity
from backend.app.models.transaction import Transaction

router = APIRouter(
    prefix="/investigation",
    tags=["Investigation"],
)


@router.get("/timeline")
def get_timeline(
    min_amount: float = Query(default=500000, gt=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    accounts = db.execute(select(Account)).scalars().all()
    entities = db.execute(select(Entity)).scalars().all()

    account_to_entity = {
        account.account_id: account.entity_id
        for account in accounts
    }

    entity_names = {
        entity.entity_id: entity.entity_name
        for entity in entities
    }

    transactions = db.execute(
        select(Transaction)
        .where(
            Transaction.status == "completed",
            Transaction.amount_eur >= min_amount,
        )
        .order_by(Transaction.transaction_date)
        .limit(limit)
    ).scalars().all()

    events = []

    for transaction in transactions:
        source_entity_id = account_to_entity.get(
            transaction.source_account_id
        )
        destination_entity_id = account_to_entity.get(
            transaction.destination_account_id
        )

        events.append(
            {
                "transaction_id": transaction.transaction_id,
                "date": transaction.transaction_date.isoformat(),
                "source_entity_id": source_entity_id,
                "source_entity_name": entity_names.get(
                    source_entity_id,
                    source_entity_id,
                ),
                "destination_entity_id": destination_entity_id,
                "destination_entity_name": entity_names.get(
                    destination_entity_id,
                    destination_entity_id,
                ),
                "amount": round(
                    float(transaction.amount_eur or transaction.amount),
                    2,
                ),
                "currency": transaction.currency,
                "transaction_type": transaction.transaction_type,
                "reference": transaction.reference,
                "description": transaction.description,
            }
        )

    return {
        "signal": "investigation_timeline",
        "min_amount": min_amount,
        "events_count": len(events),
        "events": events,
    }
