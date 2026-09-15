from collections import defaultdict

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.database.dependencies import get_db
from backend.app.models.entity import Entity

router = APIRouter(
    prefix="/investigation/anomalies",
    tags=["Investigation"],
)


@router.get("/night-access")
def detect_night_access_anomalies(
    min_night_logs: int = Query(default=10, ge=1),
    min_night_ratio: float = Query(default=0.05, gt=0, le=1),
    db: Session = Depends(get_db),
):
    from pathlib import Path

    import pandas as pd

    logs_path = Path("data/generated/audit_logs.csv")
    logs = pd.read_csv(logs_path)

    logs["timestamp"] = pd.to_datetime(logs["timestamp"])

    logs["hour"] = logs["timestamp"].dt.hour
    logs["is_night"] = logs["hour"].between(0, 5)

    total_logs = logs.groupby("employee_id").size()

    night_logs = (
        logs[logs["is_night"]]
        .groupby("employee_id")
        .size()
    )

    stats = pd.DataFrame(
        {
            "total_logs": total_logs,
            "night_logs": night_logs,
        }
    ).fillna(0)

    stats["night_ratio"] = (
        stats["night_logs"] / stats["total_logs"]
    )

    stats = stats[
        (stats["night_logs"] >= min_night_logs)
        & (stats["night_ratio"] >= min_night_ratio)
    ]

    employees = {}

    for employee_id, group in logs.groupby("employee_id"):
        employees[employee_id] = {
            "entity_id": (
                group["entity_id"].dropna().iloc[0]
                if group["entity_id"].notna().any()
                else None
            ),
        }

    entities = db.execute(
        select(Entity)
    ).scalars().all()

    entity_names = {
        entity.entity_id: entity.entity_name
        for entity in entities
    }

    anomalies = []

    for employee_id, row in stats.iterrows():
        entity_id = employees.get(
            employee_id,
            {},
        ).get("entity_id")

        anomalies.append(
            {
                "employee_id": employee_id,
                "entity_id": entity_id,
                "entity_name": entity_names.get(
                    entity_id,
                    entity_id,
                ),
                "total_logs": int(row["total_logs"]),
                "night_logs": int(row["night_logs"]),
                "night_ratio": round(
                    float(row["night_ratio"]),
                    4,
                ),
                "signal": "UNUSUAL_NIGHT_ACCESS",
            }
        )

    anomalies.sort(
        key=lambda item: (
            item["night_ratio"],
            item["night_logs"],
        ),
        reverse=True,
    )

    return {
        "signal": "unusual_night_access",
        "night_window": "00:00-05:59",
        "min_night_logs": min_night_logs,
        "min_night_ratio": min_night_ratio,
        "anomalies_detected": len(anomalies),
        "anomalies": anomalies,
    }
