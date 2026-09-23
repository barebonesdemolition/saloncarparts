from uuid import UUID

from pydantic import BaseModel, ConfigDict


class UserCreate(BaseModel):
    email: str
    password: str
    full_name: str
    phone_number: str


class CarResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    vin: str
    make: str
    model: str
    year: int | None
    trim: str | None
    engine: str | None
