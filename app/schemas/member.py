from pydantic import BaseModel, Field
from typing import Optional
from datetime import date
from app.models.member import MemberStatus


class MemberBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200, example="Max Mustermann")
    status: MemberStatus = Field(MemberStatus.aktiv, example="aktiv")
    gueltig_von: date = Field(..., example="2024-01-01")
    gueltig_bis: Optional[date] = Field(None, example=None)


class MemberCreate(MemberBase):
    """Schema für POST /members – erstellt einen neuen Eintrag."""
    pass


class MemberStatusUpdate(BaseModel):
    """
    Schema für PUT /members/{id}/status
    Schließt den aktuellen Eintrag (setzt gueltig_bis) und legt
    einen neuen Eintrag mit dem neuen Status an.
    """
    neuer_status: MemberStatus = Field(..., example="passiv")
    gueltig_ab: date = Field(..., example="2025-06-01")


class MemberResponse(MemberBase):
    id: int

    class Config:
        from_attributes = True
