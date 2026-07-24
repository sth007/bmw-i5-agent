from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class DealerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    bmw_dealer_id: str | None = Field(default=None, min_length=1, max_length=50)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=50)
    city: str | None = Field(default=None, max_length=100)


class DealerUpdate(BaseModel):
    bmw_dealer_id: str | None = Field(default=None, min_length=1, max_length=50)
    distribution_partner_id: str | None = Field(default=None, max_length=50)
    outlet_id: str | None = Field(default=None, max_length=50)
    name: str | None = Field(default=None, min_length=1, max_length=200)
    street: str | None = Field(default=None, max_length=200)
    postal_code: str | None = Field(default=None, max_length=20)
    city: str | None = Field(default=None, max_length=100)
    country: str | None = Field(default=None, max_length=10)
    latitude: float | None = None
    longitude: float | None = None
    homepage: str | None = Field(default=None, max_length=500)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=50)
    new_car_email: EmailStr | None = None
    new_car_phone: str | None = Field(default=None, max_length=50)
    used_car_email: EmailStr | None = None
    used_car_phone: str | None = Field(default=None, max_length=50)
    new_car_sales: bool | None = None
    used_car_sales: bool | None = None
    is_published: bool | None = None


class DealerImport(BaseModel):
    bmw_dealer_id: str = Field(min_length=1, max_length=50)

    distribution_partner_id: str | None = Field(default=None, max_length=50)
    outlet_id: str | None = Field(default=None, max_length=50)

    name: str = Field(min_length=1, max_length=200)

    street: str | None = Field(default=None, max_length=200)
    postal_code: str | None = Field(default=None, max_length=20)
    city: str | None = Field(default=None, max_length=100)
    country: str | None = Field(default=None, max_length=10)

    latitude: float | None = None
    longitude: float | None = None

    homepage: str | None = Field(default=None, max_length=500)

    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=50)

    new_car_email: EmailStr | None = None
    new_car_phone: str | None = Field(default=None, max_length=50)

    used_car_email: EmailStr | None = None
    used_car_phone: str | None = Field(default=None, max_length=50)

    new_car_sales: bool = False
    used_car_sales: bool = False
    is_published: bool = True

    last_sync: datetime | None = None


class DealerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    bmw_dealer_id: str
    distribution_partner_id: str | None
    outlet_id: str | None

    name: str
    street: str | None
    postal_code: str | None
    city: str | None
    country: str | None

    latitude: float | None
    longitude: float | None

    homepage: str | None
    email: EmailStr | None
    phone: str | None

    new_car_email: EmailStr | None
    new_car_phone: str | None
    used_car_email: EmailStr | None
    used_car_phone: str | None

    new_car_sales: bool
    used_car_sales: bool
    is_published: bool

    last_sync: datetime | None
    created_at: datetime
    updated_at: datetime
