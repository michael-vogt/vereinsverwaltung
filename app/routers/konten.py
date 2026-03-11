from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.konto import Konto
from app.schemas.konto import KontoCreate, KontoUpdate, KontoResponse

router = APIRouter()


def _get_or_404(konto_id: int, db: Session) -> Konto:
    konto = db.query(Konto).filter(Konto.id == konto_id).first()
    if not konto:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Konto nicht gefunden")
    return konto


@router.get("/", response_model=List[KontoResponse], summary="Alle Konten abrufen")
def get_konten(db: Session = Depends(get_db)):
    return [k for k in db.query(Konto).order_by(Konto.kontonummer).all() if k is not None]


@router.get("/{konto_id}", response_model=KontoResponse, summary="Ein Konto abrufen")
def get_konto(konto_id: int, db: Session = Depends(get_db)):
    return _get_or_404(konto_id, db)


@router.post("/", response_model=KontoResponse, status_code=status.HTTP_201_CREATED, summary="Konto anlegen")
def create_konto(payload: KontoCreate, db: Session = Depends(get_db)):
    existing = db.query(Konto).filter(Konto.kontonummer == payload.kontonummer).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Kontonummer '{payload.kontonummer}' existiert bereits.",
        )
    konto = Konto(**payload.model_dump())
    db.add(konto)
    db.commit()
    db.refresh(konto)
    return konto


@router.put("/{konto_id}", response_model=KontoResponse, summary="Konto aktualisieren")
def update_konto(konto_id: int, payload: KontoUpdate, db: Session = Depends(get_db)):
    konto = _get_or_404(konto_id, db)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(konto, field, value)
    db.commit()
    db.refresh(konto)
    return konto


@router.delete("/{konto_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Konto löschen")
def delete_konto(konto_id: int, db: Session = Depends(get_db)):
    from app.models.buchung import Buchung
    konto = _get_or_404(konto_id, db)
    in_use = db.query(Buchung).filter(
        (Buchung.sollkonto_id == konto_id) | (Buchung.habenkonto_id == konto_id)
    ).first()
    if in_use:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Konto kann nicht gelöscht werden, da es in Buchungen verwendet wird.",
        )
    db.delete(konto)
    db.commit()
