import enum
from sqlalchemy import Column, Integer, String, Date, Enum
from app.database import Base


class MemberStatus(str, enum.Enum):
    aktiv = "aktiv"
    passiv = "passiv"
    gast = "gast"
    ausgetreten = "ausgetreten"


class Member(Base):
    __tablename__ = "members"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, index=True)
    status = Column(Enum(MemberStatus), nullable=False, default=MemberStatus.aktiv)

    # Historisierung
    gueltig_von = Column(Date, nullable=False)
    gueltig_bis = Column(Date, nullable=True)  # NULL = aktuell gültiger Eintrag
