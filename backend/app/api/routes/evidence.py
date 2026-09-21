from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.database.dependencies import get_db
from backend.app.models.entity import Entity
from backend.app.models.transaction import Transaction

router = APIRouter(
    prefix="/investigation",
    tags=["Investigation"],
)


@router.get("/evidence")
def get_evidence(
    db: Session = Depends(get_db),
):
    entities = db.execute(
        select(Entity)
    ).scalars().all()

    transactions = db.execute(
        select(Transaction)
        .where(
            Transaction.status == "completed",
            Transaction.source_entity_id != Transaction.destination_entity_id,
        )
        .order_by(Transaction.amount_eur.desc())
        .limit(50)
    ).scalars().all()

    entity_names = {
        entity.entity_id: entity.entity_name
        for entity in entities
    }

    evidence = []

    for transaction in transactions:
        source_entity_id = transaction.source_entity_id
        destination_entity_id = transaction.destination_entity_id

        if source_entity_id == destination_entity_id:
            continue

        evidence.append(
            {
                "evidence_id": (
                    f"TRX-EVIDENCE-{transaction.transaction_id}"
                ),
                "type": "large_transaction",
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
                    float(
                        transaction.amount_eur
                        if transaction.amount_eur is not None
                        else transaction.amount
                    ),
                    2,
                ),
                "currency": transaction.currency,
                "transaction_type": transaction.transaction_type,
                "reference": transaction.reference,
                "description": transaction.description,
            }
        )

    return {
        "signal": "investigation_evidence",
        "evidence_count": len(evidence),
        "evidence": evidence,
    }
