from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database.session import get_db
from app.schemas.campaign import AdminResetRequest, AdminResetResponse, AdminResetStatusResponse
from app.services.admin_reset_service import AdminResetService


router = APIRouter(prefix="/api/admin", tags=["admin"])
DatabaseSession = Annotated[Session, Depends(get_db)]


def _assert_reset_enabled(reset_token: str | None) -> None:
    if settings.app_env not in {"development", "test"} or not settings.allow_test_reset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")
    if reset_token != settings.test_reset_token:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


@router.post("/reset-test-state", response_model=AdminResetResponse)
def reset_test_state(
    payload: AdminResetRequest,
    db: DatabaseSession,
    x_reset_token: str | None = Header(default=None, alias="X-Reset-Token"),
) -> AdminResetResponse:
    _assert_reset_enabled(x_reset_token)
    if payload.scope == "all_application_data" and payload.confirm != "RESET":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="confirm must be RESET for all_application_data.")
    service = AdminResetService(db)
    if payload.scope == "all_application_data":
        return service.reset_all_application_data()
    return service.reset_campaign_data()


@router.get("/reset-status", response_model=AdminResetStatusResponse)
def reset_status(
    db: DatabaseSession,
    x_reset_token: str | None = Header(default=None, alias="X-Reset-Token"),
) -> AdminResetStatusResponse:
    _assert_reset_enabled(x_reset_token)
    service = AdminResetService(db)
    return service.get_status(settings.app_env, settings.allow_test_reset)
