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


@router.get("/concentration")
def detect_concentration_anomalies(
    min_volume: float = Query(default=100000, gt=0),
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

    flows = defaultdict(lambda: defaultdict(float))
    totals = defaultdict(float)
    transaction_counts = defaultdict(int)

    for transaction in transactions:
        source_entity = account_to_entity.get(
            transaction.source_account_id
        )
        destination_entity = account_to_entity.get(
            transaction.destination_account_id
        )

        if not source_entity or not destination_entity:
            continue

        amount = float(
            transaction.amount_eur or transaction.amount
        )

        if amount <= 0:
            continue

        flows[source_entity][destination_entity] += amount
        totals[source_entity] += amount
        transaction_counts[source_entity] += 1

    anomalies = []

    for entity_id, counterparties in flows.items():
        total = totals[entity_id]

        if total < min_volume:
            continue

        top_counterparty_id, top_amount = max(
            counterparties.items(),
            key=lambda item: item[1],
        )

        concentration = top_amount / total

        if concentration >= 0.75:
            anomalies.append(
                {
                    "entity_id": entity_id,
                    "entity_name": entity_names.get(
                        entity_id,
                        entity_id,
                    ),
                    "counterparty_id": top_counterparty_id,
                    "counterparty_name": entity_names.get(
                        top_counterparty_id,
                        top_counterparty_id,
                    ),
                    "total_flow": round(total, 2),
                    "counterparty_flow": round(top_amount, 2),
                    "concentration": round(
                        concentration,
                        4,
                    ),
                    "transaction_count": transaction_counts[
                        entity_id
                    ],
                    "signal": "HIGH_COUNTERPARTY_CONCENTRATION",
                }
            )

    anomalies.sort(
        key=lambda item: (
            item["concentration"],
            item["total_flow"],
        ),
        reverse=True,
    )

    return {
        "signal": "counterparty_concentration",
        "threshold": 0.75,
        "min_volume": min_volume,
        "anomalies_detected": len(anomalies),
        "anomalies": anomalies,
    }
