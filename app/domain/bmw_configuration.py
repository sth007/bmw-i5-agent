from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, field_validator


class BMWConfiguration(BaseModel):
    configuration_id: str = Field(min_length=1)
    configuration_url: HttpUrl

    model: str = Field(min_length=1)
    variant: str = Field(min_length=1)
    package: str | None = None

    list_price: Decimal | None = Field(default=None, ge=0)
    maximum_target_price: Decimal = Field(ge=0)

    payment_preference: Literal["cash", "financing", "either"] = "cash"
    equipment: list[str] = Field(default_factory=list)

    @field_validator("configuration_id", "model", "variant")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Wert darf nicht leer sein")

        return value

    @field_validator("package")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None

        value = value.strip()
        return value or None

    @field_validator("equipment")
    @classmethod
    def normalize_equipment(cls, values: list[str]) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()

        for value in values:
            cleaned = value.strip()

            if not cleaned:
                continue

            key = cleaned.casefold()

            if key not in seen:
                normalized.append(cleaned)
                seen.add(key)

        return normalized