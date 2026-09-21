from collections import defaultdict

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.database.dependencies import get_db
from backend.app.models.entity import Entity

router = APIRouter(
    prefix="/investigation",
    tags=["Investigation"],
)


@router.get("/entity-network")
def get_entity_network(
    db: Session = Depends(get_db),
):
    entities = db.execute(
        select(Entity)
    ).scalars().all()

    entity_names = {
        entity.entity_id: entity.entity_name
        for entity in entities
    }

    nodes = []
    edges = defaultdict(
        lambda: {
            "relation_count": 0,
            "relation_types": set(),
        }
    )

    for entity in entities:
        nodes.append(
            {
                "entity_id": entity.entity_id,
                "entity_name": entity.entity_name,
                "entity_type": entity.entity_type,
                "country": entity.country,
                "city": entity.city,
            }
        )

        if entity.parent_entity_id:
            key = (
                entity.parent_entity_id,
                entity.entity_id,
            )

            edges[key]["relation_count"] += 1
            edges[key]["relation_types"].add("parent_subsidiary")

    network_edges = []

    for (source_id, target_id), data in edges.items():
        network_edges.append(
            {
                "source_entity_id": source_id,
                "source_entity_name": entity_names.get(
                    source_id,
                    source_id,
                ),
                "target_entity_id": target_id,
                "target_entity_name": entity_names.get(
                    target_id,
                    target_id,
                ),
                "relation_count": data["relation_count"],
                "relation_types": sorted(
                    data["relation_types"]
                ),
            }
        )

    return {
        "signal": "entity_network_analysis",
        "nodes_count": len(nodes),
        "edges_count": len(network_edges),
        "nodes": nodes,
        "edges": network_edges,
    }
