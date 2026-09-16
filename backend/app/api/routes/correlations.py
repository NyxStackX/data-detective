from collections import defaultdict
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Depends
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


@router.get("/correlations")
def detect_correlations(db: Session = Depends(get_db)):
    entities = db.execute(select(Entity)).scalars().all()
    accounts = db.execute(select(Account)).scalars().all()
    transactions = db.execute(
        select(Transaction).where(Transaction.status == "completed")
    ).scalars().all()

    entity_names = {
        entity.entity_id: entity.entity_name
        for entity in entities
    }

    account_to_entity = {
        account.account_id: account.entity_id
        for account in accounts
    }

    concentration_entities = set()
    flows = defaultdict(lambda: defaultdict(float))
    totals = defaultdict(float)

    for transaction in transactions:
        source_entity = account_to_entity.get(transaction.source_account_id)
        destination_entity = account_to_entity.get(
            transaction.destination_account_id
        )

        if not source_entity or not destination_entity:
            continue

        if source_entity == destination_entity:
            continue

        amount = float(transaction.amount_eur or transaction.amount)

        if amount <= 0:
            continue

        flows[source_entity][destination_entity] += amount
        totals[source_entity] += amount

    for entity_id, counterparties in flows.items():
        total = totals[entity_id]

        if total < 100000:
            continue

        _, top_amount = max(
            counterparties.items(),
            key=lambda item: item[1],
        )

        concentration = top_amount / total

        if concentration >= 0.75:
            concentration_entities.add(entity_id)

    repeated_entities = set()
    repeated_transfers = defaultdict(
        lambda: defaultdict(
            lambda: {
                "count": 0,
                "volume": 0.0,
            }
        )
    )

    for transaction in transactions:
        source_entity = account_to_entity.get(transaction.source_account_id)
        destination_entity = account_to_entity.get(
            transaction.destination_account_id
        )

        if not source_entity or not destination_entity:
            continue

        if source_entity == destination_entity:
            continue

        amount = float(transaction.amount_eur or transaction.amount)

        if amount <= 0:
            continue

        pair = repeated_transfers[source_entity][destination_entity]
        pair["count"] += 1
        pair["volume"] += amount

    for source_entity, counterparties in repeated_transfers.items():
        for destination_entity, data in counterparties.items():
            if data["count"] >= 10 and data["volume"] >= 1000000:
                repeated_entities.add(source_entity)
                repeated_entities.add(destination_entity)

    night_entities = set()

    logs_path = Path("data/generated/audit_logs.csv")
    logs = pd.read_csv(logs_path)

    logs["timestamp"] = pd.to_datetime(logs["timestamp"])
    logs["hour"] = logs["timestamp"].dt.hour
    logs["is_night"] = logs["hour"].between(0, 5)

    total_logs = logs.groupby("employee_id").size()
    night_logs = logs[logs["is_night"]].groupby("employee_id").size()

    stats = pd.DataFrame(
        {
            "total_logs": total_logs,
            "night_logs": night_logs,
        }
    ).fillna(0)

    stats["night_ratio"] = stats["night_logs"] / stats["total_logs"]

    stats = stats[
        (stats["night_logs"] >= 10)
        & (stats["night_ratio"] >= 0.05)
    ]

    for employee_id in stats.index:
        employee_logs = logs[
            logs["employee_id"] == employee_id
        ]

        entity_ids = employee_logs["entity_id"].dropna()

        if not entity_ids.empty:
            night_entities.add(entity_ids.iloc[0])

    signal_definitions = {
        "concentration": concentration_entities,
        "repeated_transfers": repeated_entities,
        "night_access": night_entities,
    }

    all_entities = set().union(*signal_definitions.values())

    results = []

    for entity_id in all_entities:
        signals = [
            signal_name
            for signal_name, entity_ids in signal_definitions.items()
            if entity_id in entity_ids
        ]

        if len(signals) < 2:
            continue

        score = 0

        if "concentration" in signals:
            score += 3

        if "repeated_transfers" in signals:
            score += 2

        if "night_access" in signals:
            score += 2

        results.append(
            {
                "entity_id": entity_id,
                "entity_name": entity_names.get(
                    entity_id,
                    entity_id,
                ),
                "signal_count": len(signals),
                "score": score,
                "signals": signals,
            }
        )

    results.sort(
        key=lambda item: (
            item["signal_count"],
            item["score"],
            item["entity_name"],
        ),
        reverse=True,
    )

    return {
        "signal": "correlated_investigation_lead",
        "minimum_signals": 2,
        "scoring": {
            "concentration": 3,
            "repeated_transfers": 2,
            "night_access": 2,
        },
        "leads_detected": len(results),
        "leads": results,
    }
