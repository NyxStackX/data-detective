from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.database.dependencies import get_db
from backend.app.models.entity import Entity

router = APIRouter(
    prefix="/investigation",
    tags=["Investigation"],
)


def clean_value(value):
    if pd.isna(value):
        return None
    return value


@router.get("/people")
def get_people(
    db: Session = Depends(get_db),
):
    employees_path = Path("data/generated/employees.csv")
    officers_path = Path("data/generated/company_officers.csv")

    employees = pd.read_csv(employees_path)
    officers = pd.read_csv(officers_path)

    entities = db.execute(select(Entity)).scalars().all()

    entity_names = {
        entity.entity_id: entity.entity_name
        for entity in entities
    }

    people = []

    for _, employee in employees.iterrows():
        entity_id = clean_value(employee["entity_id"])

        people.append(
            {
                "person_id": clean_value(employee["employee_id"]),
                "name": (
                    f"{employee['first_name']} {employee['last_name']}"
                ),
                "role": clean_value(employee["position"]),
                "department": clean_value(employee["department"]),
                "entity_id": entity_id,
                "entity_name": entity_names.get(
                    entity_id,
                    entity_id,
                ),
                "authorization_level": (
                    int(employee["authorization_level"])
                    if not pd.isna(employee["authorization_level"])
                    else None
                ),
                "status": clean_value(employee["status"]),
                "start_date": clean_value(employee["hire_date"]),
                "end_date": clean_value(employee["termination_date"]),
                "source": "employee",
            }
        )

    for _, officer in officers.iterrows():
        entity_id = clean_value(officer["company_id"])

        people.append(
            {
                "person_id": clean_value(officer["officer_id"]),
                "name": (
                    f"{officer['first_name']} {officer['last_name']}"
                ),
                "role": clean_value(officer["role"]),
                "department": None,
                "entity_id": entity_id,
                "entity_name": entity_names.get(
                    entity_id,
                    entity_id,
                ),
                "authorization_level": None,
                "status": "active",
                "start_date": clean_value(
                    officer["appointment_date"]
                ),
                "end_date": None,
                "source": "company_officer",
            }
        )

    return {
        "signal": "people_entity_analysis",
        "people_count": len(people),
        "employees_count": len(employees),
        "officers_count": len(officers),
        "people": people,
    }
