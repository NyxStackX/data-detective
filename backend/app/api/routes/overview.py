from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.database.dependencies import get_db
from backend.app.models.account import Account
from backend.app.models.entity import Entity
from backend.app.models.transaction import Transaction


router = APIRouter(prefix="/overview", tags=["Overview"])


@router.get("")
def get_overview(db: Session = Depends(get_db)):
    entities_count = db.scalar(
        select(func.count()).select_from(Entity)
    )

    accounts_count = db.scalar(
        select(func.count()).select_from(Account)
    )

    transactions_count = db.scalar(
        select(func.count()).select_from(Transaction)
    )

    return {
        "case": "CASE #001 - THE MISSING FORTUNE",
        "status": "active",
        "statistics": {
            "entities": entities_count,
            "accounts": accounts_count,
            "transactions": transactions_count,
        },
    }
