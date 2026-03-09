from sqlalchemy import Column, Integer, String, Numeric, Date, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class Buchung(Base):
    __tablename__ = "buchungen"

    id = Column(Integer, primary_key=True, index=True)
    sollkonto_id = Column(Integer, ForeignKey("kontenrahmen.id"), nullable=False)
    habenkonto_id = Column(Integer, ForeignKey("kontenrahmen.id"), nullable=False)
    betrag = Column(Numeric(12, 2), nullable=False)
    buchungsdatum = Column(Date, nullable=False)
    buchungstext = Column(String(500), nullable=True)
    mitglied_id = Column(Integer, ForeignKey("members.id"), nullable=True)

    # Beziehungen für komfortables Laden
    sollkonto = relationship("Konto", foreign_keys=[sollkonto_id])
    habenkonto = relationship("Konto", foreign_keys=[habenkonto_id])
    mitglied = relationship("Member", foreign_keys=[mitglied_id])
