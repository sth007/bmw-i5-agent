from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.vehicle_configuration import BMWConfigurationParseRequest, BMWConfigurationParseResponse
from app.services.bmw_configuration_parser import (
    BMWConfigurationParserError,
    BMWConfigurationParserService,
    BMWConfigurationResolutionError,
)


router = APIRouter(prefix="/api/configurations", tags=["configurations"])
DatabaseSession = Annotated[Session, Depends(get_db)]


@router.post("/parse-bmw", response_model=BMWConfigurationParseResponse, status_code=status.HTTP_200_OK)
def parse_bmw_configuration(
    payload: BMWConfigurationParseRequest,
    db: DatabaseSession,
) -> BMWConfigurationParseResponse:
    service = BMWConfigurationParserService(db)
    try:
        entity = service.parse_and_store(payload.configuration_url)
    except BMWConfigurationParserError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except BMWConfigurationResolutionError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return BMWConfigurationParseResponse.model_validate(entity.normalized_data)
