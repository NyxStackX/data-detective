from fastapi import FastAPI

from backend.app.api.routes.anomalies import router as anomalies_router
from backend.app.api.routes.entities import router as entities_router
from backend.app.api.routes.investigation import router as investigation_router
from backend.app.api.routes.financial_flows import router as financial_flows_router
from backend.app.api.routes.entity_network import router as entity_network_router
from backend.app.api.routes.people import router as people_router
from backend.app.api.routes.evidence import router as evidence_router
from backend.app.api.routes.overview import router as overview_router
from backend.app.api.routes.anomalies_repeated import router as repeated_anomalies_router
from backend.app.api.routes.anomalies_night import router as night_anomalies_router
from backend.app.api.routes.correlations import router as correlations_router
from backend.app.api.routes.timeline import router as timeline_router
from backend.app.api.routes.transactions import router as transactions_router


app = FastAPI(
    title="DATA DETECTIVE API",
    description="Private Intelligence Investigation Platform",
    version="1.0.0",
)

app.include_router(overview_router)
app.include_router(transactions_router)
app.include_router(anomalies_router)
app.include_router(repeated_anomalies_router)
app.include_router(night_anomalies_router)
app.include_router(correlations_router)
app.include_router(timeline_router)
app.include_router(entities_router)
app.include_router(investigation_router)
app.include_router(financial_flows_router)
app.include_router(entity_network_router)
app.include_router(people_router)
app.include_router(evidence_router)


@app.get("/")
def root():
    return {
        "name": "DATA DETECTIVE",
        "status": "online",
        "case": "CASE #001 - THE MISSING FORTUNE",
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
    }
