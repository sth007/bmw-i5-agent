from datetime import datetime
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, EmailStr, Field, HttpUrl, field_validator


class ContactStatus(StrEnum):
    NOT_CONTACTED = "not_contacted"
    PREPARED = "prepared"
    CONTACTED = "contacted"
    REPLIED = "replied"
    NO_RESPONSE = "no_response"
    BLOCKED = "blocked"


class Dealer(BaseModel):
    dealer_id: Annotated[str, Field(min_length=1)]
    name: Annotated[str, Field(min_length=1)]

    dealer_group: str | None = None
    branch_name: str | None = None

    street: str | None = None
    postal_code: str | None = None
    city: Annotated[str, Field(min_length=1)]
    country: str = "Deutschland"

    sales_email: EmailStr | None = None
    website_url: HttpUrl | None = None
    contact_form_url: HttpUrl | None = None

    is_authorized_bmw_partner: bool = True

    contact_status: ContactStatus = ContactStatus.NOT_CONTACTED
    last_contacted_at: datetime | None = None

    do_not_contact: bool = False
    notes: str | None = None

    @field_validator(
        "dealer_id",
        "name",
        "city",
        "dealer_group",
        "branch_name",
        "street",
        "postal_code",
        "country",
        "notes",
    )
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        if value is None:
            return None

        cleaned = value.strip()
        return cleaned or None

    @field_validator("city")
    @classmethod
    def city_must_not_be_empty(cls, value: str | None) -> str:
        if not value:
            raise ValueError("Stadt darf nicht leer sein")

        return value

    def can_be_contacted(self) -> bool:
        return (
            self.is_authorized_bmw_partner
            and not self.do_not_contact
            and self.contact_status != ContactStatus.BLOCKED
            and (self.sales_email is not None or self.contact_form_url is not None)
        )