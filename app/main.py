from fastapi import FastAPI

from app.api.admin import router as admin_router
from app.api.campaigns import router as campaigns_router
from app.api.campaigns import contact_router as campaign_contacts_router
from app.api.campaigns import start_router as campaign_start_router
from app.api.dealers import debug_router as dealers_debug_router
from app.api.dealers import router as dealers_router
from app.api.inbound_emails import router as inbound_emails_router
from app.api.inbound_emails import review_router as review_queue_router
from app.api.offers import router as offers_router
from app.config import settings


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
)

app.include_router(offers_router)
app.include_router(dealers_router)
app.include_router(dealers_debug_router)
app.include_router(campaigns_router)
app.include_router(campaign_start_router)
app.include_router(campaign_contacts_router)
app.include_router(inbound_emails_router)
app.include_router(review_queue_router)
app.include_router(admin_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
