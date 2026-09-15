from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.database.dependencies import get_db
from backend.app.models.entity import Entity


router = APIRouter(prefix="/entities", tags=["Entities"])


@router.get("")
def get_entities(
    search: str | None = Query(default=None),
    entity_type: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    query = select(Entity)

    if search:
        query = query.where(
            Entity.entity_name.ilike(f"%{search}%")
        )

    if entity_type:
        query = query.where(
            Entity.entity_type.ilike(entity_type)
        )

    query = query.order_by(Entity.entity_name)

    entities = db.execute(query).scalars().all()

    return {
        "count": len(entities),
        "entities": [
            {
                "entity_id": entity.entity_id,
                "entity_name": entity.entity_name,
                "entity_type": entity.entity_type,
                "parent_entity_id": entity.parent_entity_id,
                "country": entity.country,
                "city": entity.city,
                "industry": entity.industry,
                "creation_date": (
                    entity.creation_date.isoformat()
                    if entity.creation_date
                    else None
                ),
                "status": entity.status,
            }
            for entity in entities
        ],
    }
