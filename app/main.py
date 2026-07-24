from fastapi import FastAPI

from app.api.offers import router as offers_router
from app.api.dealers import router as dealers_router

app = FastAPI(
    title="BMW Agent",
    version="0.1.0",
)

app.include_router(offers_router)
app.include_router(dealers_router)

@app.get("/health")
def health():
    return {"status": "ok"}