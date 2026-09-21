from collections import defaultdict

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


@router.get("/financial-flows")
def get_financial_flows(
    min_volume: float = Query(default=100000, gt=0),
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
        select(Transaction).where(
            Transaction.status == "completed"
        )
    ).scalars().all()

    flows = defaultdict(
        lambda: {
            "transaction_count": 0,
            "total_volume": 0.0,
        }
    )

    for transaction in transactions:
        source_entity_id = account_to_entity.get(
            transaction.source_account_id
        )
        destination_entity_id = account_to_entity.get(
            transaction.destination_account_id
        )

        if not source_entity_id or not destination_entity_id:
            continue

        if source_entity_id == destination_entity_id:
            continue

        amount = float(
            transaction.amount_eur
            if transaction.amount_eur is not None
            else transaction.amount
        )

        if amount <= 0:
            continue

        key = (
            source_entity_id,
            destination_entity_id,
        )

        flows[key]["transaction_count"] += 1
        flows[key]["total_volume"] += amount

    results = []

    for (source_entity_id, destination_entity_id), data in flows.items():
        if data["total_volume"] < min_volume:
            continue

        results.append(
            {
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
                "transaction_count": data["transaction_count"],
                "total_volume": round(
                    data["total_volume"],
                    2,
                ),
                "average_transaction_amount": round(
                    data["total_volume"]
                    / data["transaction_count"],
                    2,
                ),
            }
        )

    results.sort(
        key=lambda item: (
            item["total_volume"],
            item["transaction_count"],
        ),
        reverse=True,
    )

    return {
        "signal": "financial_flow_analysis",
        "min_volume": min_volume,
        "flows_detected": len(results),
        "flows": results[:limit],
    }
