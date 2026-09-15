from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.database.dependencies import get_db
from backend.app.models.account import Account
from backend.app.models.entity import Entity
from backend.app.models.transaction import Transaction


router = APIRouter(
    prefix="/investigation",
    tags=["Investigation"],
)


@router.get("")
def get_investigation(db: Session = Depends(get_db)):
    entities = db.execute(
        select(Entity)
    ).scalars().all()

    results = []

    for entity in entities:
        account_ids = db.execute(
            select(Account.account_id).where(
                Account.entity_id == entity.entity_id
            )
        ).scalars().all()

        if not account_ids:
            continue

        incoming = db.scalar(
            select(func.coalesce(func.sum(Transaction.amount_eur), 0))
            .where(
                Transaction.destination_account_id.in_(account_ids),
                Transaction.status == "completed",
            )
        )

        outgoing = db.scalar(
            select(func.coalesce(func.sum(Transaction.amount_eur), 0))
            .where(
                Transaction.source_account_id.in_(account_ids),
                Transaction.status == "completed",
            )
        )

        incoming = float(incoming or 0)
        outgoing = float(outgoing or 0)

        if incoming == 0 and outgoing == 0:
            continue

        flow_ratio = (
            outgoing / incoming
            if incoming > 0
            else 0
        )

        results.append(
            {
                "entity_id": entity.entity_id,
                "entity_name": entity.entity_name,
                "entity_type": entity.entity_type,
                "country": entity.country,
                "city": entity.city,
                "incoming_amount": round(incoming, 2),
                "outgoing_amount": round(outgoing, 2),
                "flow_ratio": round(flow_ratio, 4),
            }
        )

    results.sort(
        key=lambda item: item["outgoing_amount"],
        reverse=True,
    )

    return {
        "case": "CASE #001 - THE MISSING FORTUNE",
        "status": "active",
        "entities_analyzed": len(results),
        "results": results,
    }
