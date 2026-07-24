from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.dealer import DealerCreate, DealerImport, DealerResponse
from app.services.dealer_service import DealerService


router = APIRouter(
    prefix="/dealers",
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