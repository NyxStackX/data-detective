from fastapi import APIRouter, Query

from backend.app.services.data_loader import load_entities


router = APIRouter(prefix="/entities", tags=["Entities"])


@router.get("")
def get_entities(
    search: str | None = Query(default=None),
    entity_type: str | None = Query(default=None),
):
    entities = load_entities()

    if search:
        mask = entities["entity_name"].str.contains(
            search,
            case=False,
            na=False,
        )
        entities = entities[mask]

    if entity_type:
        entities = entities[
            entities["entity_type"].str.lower() == entity_type.lower()
        ]

    return {
        "count": len(entities),
        "entities": entities.to_dict(orient="records"),
    }
