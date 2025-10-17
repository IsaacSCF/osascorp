from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    action = Column(String, nullable=False)  # e.g., "create", "update", "delete"
    target_table = Column(String, nullable=False)  # e.g., "orgs"
    target_id = Column(Integer, nullable=False)
    details = Column(String)  # JSON string with changes
    created_at = Column(DateTime(timezone=True), server_default=func.now())
