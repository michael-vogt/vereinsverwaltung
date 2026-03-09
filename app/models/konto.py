from sqlalchemy import Column, Integer, String
from app.database import Base


class Konto(Base):
    __tablename__ = "kontenrahmen"

    id = Column(Integer, primary_key=True, index=True)
    kontonummer = Column(String(20), nullable=False, unique=True, index=True)
    kontoname = Column(String(200), nullable=False)
