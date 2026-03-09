from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date

from app.database import get_db
from app.models.member import Member, MemberStatus
from app.schemas.member import MemberCreate, MemberStatusUpdate, MemberResponse

router = APIRouter()


def _get_or_404(member_id: int, db: Session) -> Member:
    member = db.query(Member).filter(Member.id == member_id).first()
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mitglied nicht gefunden")
    return member


# ---------------------------------------------------------------------------
# Lesen
# ---------------------------------------------------------------------------

@router.get("/", response_model=List[MemberResponse], summary="Alle Einträge abrufen")
def get_members(
    nur_aktuell: bool = True,
    mitglied_status: Optional[MemberStatus] = None,
    db: Session = Depends(get_db),
):
    """
    Gibt Mitglieder zurück.
    - `nur_aktuell=true` (Standard): nur Einträge ohne `gueltig_bis` (aktuell gültig)
    - `nur_aktuell=false`: gesamte Historie aller Einträge
    - `mitglied_status`: optionaler Filter nach Status
    """
    q = db.query(Member)
    if nur_aktuell:
        q = q.filter(Member.gueltig_bis == None)
    if mitglied_status:
        q = q.filter(Member.status == mitglied_status)
    return q.order_by(Member.name).all()


@router.get("/{member_id}", response_model=MemberResponse, summary="Ein Mitglied abrufen")
def get_member(member_id: int, db: Session = Depends(get_db)):
    """Gibt einen einzelnen Eintrag anhand der ID zurück."""
    return _get_or_404(member_id, db)


@router.get("/{member_id}/historie", response_model=List[MemberResponse], summary="Historie eines Mitglieds")
def get_member_history(member_id: int, db: Session = Depends(get_db)):
    """
    Gibt alle historischen Einträge zu einem Mitglied zurück,
    geordnet nach `gueltig_von`.
    Mitglieder werden über den Namen identifiziert.
    """
    member = _get_or_404(member_id, db)
    history = (
        db.query(Member)
        .filter(Member.name == member.name)
        .order_by(Member.gueltig_von)
        .all()
    )
    return history


# ---------------------------------------------------------------------------
# Schreiben
# ---------------------------------------------------------------------------

@router.post("/", response_model=MemberResponse, status_code=status.HTTP_201_CREATED, summary="Mitglied anlegen")
def create_member(payload: MemberCreate, db: Session = Depends(get_db)):
    """Legt ein neues Mitglied an."""
    member = Member(**payload.model_dump())
    db.add(member)
    db.commit()
    db.refresh(member)
    return member


@router.put("/{member_id}/status", response_model=MemberResponse, summary="Status ändern (historisiert)")
def update_status(member_id: int, payload: MemberStatusUpdate, db: Session = Depends(get_db)):
    """
    Historisierter Statuswechsel:
    1. Aktuellen Eintrag abschließen (`gueltig_bis = gueltig_ab - 1 Tag`)
    2. Neuen Eintrag mit neuem Status anlegen (`gueltig_von = gueltig_ab`)
    """
    current = _get_or_404(member_id, db)

    if current.gueltig_bis is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Dieser Eintrag ist bereits historisiert (gueltig_bis gesetzt).",
        )
    if payload.gueltig_ab <= current.gueltig_von:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="gueltig_ab muss nach dem gueltig_von des aktuellen Eintrags liegen.",
        )

    from datetime import timedelta

    # Alten Eintrag abschließen
    current.gueltig_bis = payload.gueltig_ab - timedelta(days=1)

    # Neuen Eintrag erstellen
    new_entry = Member(
        name=current.name,
        status=payload.neuer_status,
        gueltig_von=payload.gueltig_ab,
        gueltig_bis=None,
    )
    db.add(new_entry)
    db.commit()
    db.refresh(new_entry)
    return new_entry


@router.delete("/{member_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Eintrag löschen")
def delete_member(member_id: int, db: Session = Depends(get_db)):
    """Löscht einen einzelnen Eintrag (nicht die gesamte Historie)."""
    member = _get_or_404(member_id, db)
    db.delete(member)
    db.commit()
