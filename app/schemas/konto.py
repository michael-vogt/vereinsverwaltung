from pydantic import BaseModel, Field
from typing import Optional


class KontoBase(BaseModel):
    kontonummer: str = Field(..., min_length=1, max_length=20, example="1000")
    kontoname: str = Field(..., min_length=1, max_length=200, example="Kasse")


class KontoCreate(KontoBase):
    pass


class KontoUpdate(BaseModel):
    kontonummer: Optional[str] = Field(None, min_length=1, max_length=20)
    kontoname: Optional[str] = Field(None, min_length=1, max_length=200)


class KontoResponse(KontoBase):
    id: int

    class Config:
        from_attributes = True
