from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from datetime import date

from app.database import get_db
from app.models.buchung import Buchung
from app.models.konto import Konto
from app.models.member import Member
from app.schemas.buchung import BuchungCreate, BuchungUpdate, BuchungResponse

router = APIRouter()


def _get_or_404(buchung_id: int, db: Session) -> Buchung:
    b = (
        db.query(Buchung)
        .options(joinedload(Buchung.sollkonto), joinedload(Buchung.habenkonto), joinedload(Buchung.mitglied))
        .filter(Buchung.id == buchung_id)
        .first()
    )
    if not b:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Buchung nicht gefunden")
    return b


def _validate_fks(payload, db: Session):
    """Prüft, ob referenzierte Konten und Mitglied existieren."""
    if not db.query(Konto).filter(Konto.id == payload.sollkonto_id).first():
        raise HTTPException(status_code=422, detail=f"Sollkonto ID {payload.sollkonto_id} nicht gefunden.")
    if not db.query(Konto).filter(Konto.id == payload.habenkonto_id).first():
        raise HTTPException(status_code=422, detail=f"Habenkonto ID {payload.habenkonto_id} nicht gefunden.")
    if payload.mitglied_id and not db.query(Member).filter(Member.id == payload.mitglied_id).first():
        raise HTTPException(status_code=422, detail=f"Mitglied ID {payload.mitglied_id} nicht gefunden.")


@router.get("/", response_model=List[BuchungResponse], summary="Buchungen abrufen")
def get_buchungen(
    von: Optional[date] = None,
    bis: Optional[date] = None,
    mitglied_id: Optional[int] = None,
    konto_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """
    Buchungen abrufen mit optionalen Filtern:
    - `von` / `bis`: Datumsbereich
    - `mitglied_id`: nur Buchungen eines Mitglieds
    - `konto_id`: Buchungen, in denen das Konto als Soll oder Haben vorkommt
    """
    q = db.query(Buchung).options(
        joinedload(Buchung.sollkonto),
        joinedload(Buchung.habenkonto),
        joinedload(Buchung.mitglied),
    )
    if von:
        q = q.filter(Buchung.buchungsdatum >= von)
    if bis:
        q = q.filter(Buchung.buchungsdatum <= bis)
    if mitglied_id:
        q = q.filter(Buchung.mitglied_id == mitglied_id)
    if konto_id:
        q = q.filter((Buchung.sollkonto_id == konto_id) | (Buchung.habenkonto_id == konto_id))
    return q.order_by(Buchung.buchungsdatum.desc()).all()


@router.get("/{buchung_id}", response_model=BuchungResponse, summary="Eine Buchung abrufen")
def get_buchung(buchung_id: int, db: Session = Depends(get_db)):
    return _get_or_404(buchung_id, db)


@router.post("/", response_model=BuchungResponse, status_code=status.HTTP_201_CREATED, summary="Buchung erstellen")
def create_buchung(payload: BuchungCreate, db: Session = Depends(get_db)):
    _validate_fks(payload, db)
    buchung = Buchung(**payload.model_dump())
    db.add(buchung)
    db.commit()
    return _get_or_404(buchung.id, db)


@router.put("/{buchung_id}", response_model=BuchungResponse, summary="Buchung korrigieren")
def update_buchung(buchung_id: int, payload: BuchungUpdate, db: Session = Depends(get_db)):
    """Nur Buchungstext, -datum und Mitgliederreferenz sind nachträglich änderbar."""
    buchung = _get_or_404(buchung_id, db)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(buchung, field, value)
    db.commit()
    return _get_or_404(buchung_id, db)


@router.delete("/{buchung_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Buchung löschen")
def delete_buchung(buchung_id: int, db: Session = Depends(get_db)):
    buchung = _get_or_404(buchung_id, db)
    db.delete(buchung)
    db.commit()
