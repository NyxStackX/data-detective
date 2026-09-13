from fastapi import APIRouter, Query

from backend.app.services.data_loader import load_transactions


router = APIRouter(prefix="/transactions", tags=["Transactions"])


@router.get("")
def get_transactions(
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    transaction_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
):
    transactions = load_transactions()

    if transaction_type:
        transactions = transactions[
            transactions["transaction_type"].str.lower()
            == transaction_type.lower()
        ]

    if status:
        transactions = transactions[
            transactions["status"].str.lower()
            == status.lower()
        ]

    total = len(transactions)

    transactions = transactions.iloc[offset:offset + limit]

    transactions["transaction_date"] = (
        transactions["transaction_date"].dt.strftime("%Y-%m-%d")
    )

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "transactions": transactions.to_dict(orient="records"),
    }
