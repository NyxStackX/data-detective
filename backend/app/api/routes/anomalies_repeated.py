from collections import defaultdict

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.database.dependencies import get_db
from backend.app.models.account import Account
from backend.app.models.entity import Entity
from backend.app.models.transaction import Transaction


router = APIRouter(
    prefix="/investigation/anomalies",
    tags=["Investigation"],
)


@router.get("/repeated-transfers")
def detect_repeated_transfers(
    min_transactions: int = Query(default=10, ge=2),
    min_volume: float = Query(default=1000000, gt=0),
    db: Session = Depends(get_db),
):
    entities = db.execute(
        select(Entity)
    ).scalars().all()

    accounts = db.execute(
        select(Account)
    ).scalars().all()

    transactions = db.execute(
        select(Transaction).where(
            Transaction.status == "completed"
        )
    ).scalars().all()

    account_to_entity = {
        account.account_id: account.entity_id
        for account in accounts
    }

    entity_names = {
        entity.entity_id: entity.entity_name
        for entity in entities
    }

    transfers = defaultdict(
        lambda: defaultdict(
            lambda: {
                "count": 0,
                "volume": 0.0,
            }
        )
    )

    for transaction in transactions:
        source_entity = account_to_entity.get(
            transaction.source_account_id
        )
        destination_entity = account_to_entity.get(
            transaction.destination_account_id
        )

        if not source_entity or not destination_entity:
            continue

        if source_entity == destination_entity:
            continue

        amount = float(
            transaction.amount_eur or transaction.amount
        )

        if amount <= 0:
            continue

        pair = transfers[source_entity][destination_entity]

        pair["count"] += 1
        pair["volume"] += amount

    anomalies = []

    for source_entity, counterparties in transfers.items():
        for destination_entity, data in counterparties.items():
            if data["count"] < min_transactions:
                continue

            if data["volume"] < min_volume:
                continue

            average_amount = (
                data["volume"] / data["count"]
            )

            anomalies.append(
                {
                    "source_entity_id": source_entity,
                    "source_entity_name": entity_names.get(
                        source_entity,
                        source_entity,
                    ),
                    "counterparty_id": destination_entity,
                    "counterparty_name": entity_names.get(
                        destination_entity,
                        destination_entity,
                    ),
                    "transaction_count": data["count"],
                    "total_volume": round(
                        data["volume"],
                        2,
                    ),
                    "average_transaction_amount": round(
                        average_amount,
                        2,
                    ),
                    "signal": "REPEATED_COUNTERPARTY_TRANSFERS",
                }
            )

    anomalies.sort(
        key=lambda item: (
            item["total_volume"],
            item["transaction_count"],
        ),
        reverse=True,
    )

    return {
        "signal": "repeated_counterparty_transfers",
        "min_transactions": min_transactions,
        "min_volume": min_volume,
        "anomalies_detected": len(anomalies),
        "anomalies": anomalies,
    }
