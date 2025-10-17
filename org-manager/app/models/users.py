from sqlalchemy import Column, Integer, String, DateTime, Enum, Boolean, Text
from sqlalchemy.sql import func
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(Enum("admin", "moderador_legal", "moderador_ilegal", "visualizador", name="user_role"), default="visualizador")
    status = Column(Enum("pendente", "aprovado", "rejeitado", "suspenso", name="user_status"), default="pendente")
    permissions = Column(Text, nullable=True)  # JSON string with specific permissions
    approved_by = Column(Integer, nullable=True)  # User ID who approved
    approved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
