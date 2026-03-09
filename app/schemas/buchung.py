from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import date
from decimal import Decimal
from app.schemas.konto import KontoResponse
from app.schemas.member import MemberResponse


class BuchungBase(BaseModel):
    sollkonto_id: int = Field(..., example=1)
    habenkonto_id: int = Field(..., example=2)
    betrag: Decimal = Field(..., gt=0, decimal_places=2, example="150.00")
    buchungsdatum: date = Field(..., example="2025-01-15")
    buchungstext: Optional[str] = Field(None, max_length=500, example="Mitgliedsbeitrag Q1")
    mitglied_id: Optional[int] = Field(None, example=1)

    @field_validator("habenkonto_id")
    @classmethod
    def soll_haben_verschieden(cls, v, info):
        if "sollkonto_id" in info.data and v == info.data["sollkonto_id"]:
            raise ValueError("Soll- und Habenkonto dürfen nicht identisch sein.")
        return v


class BuchungCreate(BuchungBase):
    pass


class BuchungUpdate(BaseModel):
    buchungstext: Optional[str] = Field(None, max_length=500)
    buchungsdatum: Optional[date] = None
    mitglied_id: Optional[int] = None


class BuchungResponse(BuchungBase):
    id: int
    sollkonto: KontoResponse
    habenkonto: KontoResponse
    mitglied: Optional[MemberResponse] = None

    class Config:
        from_attributes = True
