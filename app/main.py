from fastapi import FastAPI

from app.api.campaigns import router as campaigns_router
from app.config import settings


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
)

app.include_router(campaigns_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
