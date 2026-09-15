from fastapi import FastAPI

from backend.app.api.routes.entities import router as entities_router
from backend.app.api.routes.investigation import router as investigation_router
from backend.app.api.routes.overview import router as overview_router
from backend.app.api.routes.transactions import router as transactions_router


app = FastAPI(
    title="DATA DETECTIVE API",
    description="Private Intelligence Investigation Platform",
    version="1.0.0",
)

app.include_router(overview_router)
app.include_router(transactions_router)
app.include_router(entities_router)
app.include_router(investigation_router)


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
