from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.dealer import (
    DealerCountResponse,
    DealerCreate,
    DealerDebugSelectionResponse,
    DealerImport,
    DealerResponse,
    DealerStatisticsResponse,
    DealerUpdate,
)
from app.services.dealer_selection_service import DealerSelectionService
from app.services.dealer_service import DealerService


router = APIRouter(
    prefix="/dealers",
    tags=["dealers"],
)
debug_router = APIRouter(
    prefix="/api/dealers",
    tags=["dealers"],
)


@router.post(
    "",
    response_model=DealerResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_dealer(
    payload: DealerCreate,
    db: Session = Depends(get_db),
) -> DealerResponse:
    service = DealerService(db)

    try:
        dealer = service.create_dealer(
            name=payload.name,
            bmw_dealer_id=payload.bmw_dealer_id,
            email=str(payload.email) if payload.email else None,
            phone=payload.phone,
            city=payload.city,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return dealer


@router.post(
    "/import",
    status_code=status.HTTP_200_OK,
)
def import_dealers(
    payload: list[DealerImport],
    db: Session = Depends(get_db),
) -> dict[str, int]:
    service = DealerService(db)
    return service.import_dealers(payload)

@router.get(
    "",
    response_model=list[DealerResponse],
)
def get_dealers(
    db: Session = Depends(get_db),
) -> list[DealerResponse]:
    service = DealerService(db)
    return service.get_all_dealers()


@router.get(
    "/count",
    response_model=DealerCountResponse,
)
def get_dealer_count(
    db: Session = Depends(get_db),
) -> DealerCountResponse:
    service = DealerService(db)
    return DealerCountResponse(
        dealer_count=service.get_dealer_count()
    )


@router.get(
    "/statistics",
    response_model=DealerStatisticsResponse,
)
def get_dealer_statistics(
    db: Session = Depends(get_db),
) -> DealerStatisticsResponse:
    service = DealerService(db)
    return DealerStatisticsResponse(
        **service.get_dealer_statistics()
    )


@debug_router.get(
    "/debug-selection",
    response_model=DealerDebugSelectionResponse,
)
def get_debug_selection(
    limit: int = 3,
    db: Session = Depends(get_db),
) -> DealerDebugSelectionResponse:
    service = DealerSelectionService(db)
    return DealerDebugSelectionResponse(
        **service.debug_selection(limit)
    )


@router.get(
    "/{dealer_id}",
    response_model=DealerResponse,
)
def get_dealer(
    dealer_id: int,
    db: Session = Depends(get_db),
) -> DealerResponse:
    service = DealerService(db)
    dealer = service.get_dealer(dealer_id)

    if dealer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Händler wurde nicht gefunden.",
        )

    return dealer


@router.patch(
    "/{dealer_id}",
    response_model=DealerResponse,
)
def patch_dealer(
    dealer_id: int,
    payload: DealerUpdate,
    db: Session = Depends(get_db),
) -> DealerResponse:
    service = DealerService(db)
    dealer = service.update_dealer(dealer_id, payload)

    if dealer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Händler wurde nicht gefunden.",
        )

    return dealer


@router.delete(
    "/{dealer_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_dealer(
    dealer_id: int,
    db: Session = Depends(get_db),
) -> Response:
    service = DealerService(db)
    deleted = service.delete_dealer(dealer_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Händler wurde nicht gefunden.",
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)
