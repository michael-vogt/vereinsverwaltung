from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.item import Item
from app.schemas.item import ItemCreate, ItemUpdate, ItemResponse

router = APIRouter()


@router.get("/", response_model=List[ItemResponse], summary="Alle Items abrufen")
def get_items(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Gibt eine Liste aller Items zurück (mit Pagination)."""
    return db.query(Item).offset(skip).limit(limit).all()


@router.get("/{item_id}", response_model=ItemResponse, summary="Ein Item abrufen")
def get_item(item_id: int, db: Session = Depends(get_db)):
    """Gibt ein einzelnes Item anhand der ID zurück."""
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item nicht gefunden")
    return item


@router.post("/", response_model=ItemResponse, status_code=status.HTTP_201_CREATED, summary="Item erstellen")
def create_item(payload: ItemCreate, db: Session = Depends(get_db)):
    """Erstellt ein neues Item."""
    item = Item(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.put("/{item_id}", response_model=ItemResponse, summary="Item aktualisieren")
def update_item(item_id: int, payload: ItemUpdate, db: Session = Depends(get_db)):
    """Aktualisiert ein vorhandenes Item (nur übergebene Felder)."""
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item nicht gefunden")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(item, field, value)

    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Item löschen")
def delete_item(item_id: int, db: Session = Depends(get_db)):
    """Löscht ein Item anhand der ID."""
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item nicht gefunden")
    db.delete(item)
    db.commit()
