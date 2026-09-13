from fastapi import FastAPI

app = FastAPI(
    title="DATA DETECTIVE API",
    description="Private Intelligence Investigation Platform",
    version="1.0.0",
)


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
