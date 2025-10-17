from sqlalchemy import Column, Integer, String, Date, DateTime, Enum, Boolean, Text
from sqlalchemy.sql import func
from app.database import Base

class Org(Base):
    __tablename__ = "orgs"

    id = Column(Integer, primary_key=True, index=True)
    faccao = Column(String, nullable=False)
    tags_fabricacao = Column(Text)  # JSON string of tags list
    contato = Column(String)
    membros_ativos = Column(Integer)
    data_entrega = Column(Date)
    discord_lider = Column(String)
    tipo = Column(Enum("LEGAL", "ILEGAL", name="tipo_org"))
    ativo = Column(Boolean, default=True)
    entregue = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
