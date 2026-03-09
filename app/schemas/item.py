from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ItemBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200, example="Mein Artikel")
    description: Optional[str] = Field(None, max_length=1000, example="Eine Beschreibung")
    active: bool = True


class ItemCreate(ItemBase):
    """Schema für POST /items"""
    pass


class ItemUpdate(BaseModel):
    """Schema für PUT /items/{id} – alle Felder optional"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    active: Optional[bool] = None


class ItemResponse(ItemBase):
    """Schema für Antworten"""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True  # SQLAlchemy-Objekte direkt serialisieren
