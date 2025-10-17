from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class AuditLogResponse(BaseModel):
    id: int
    user_id: Optional[int]
    action: str
    target_table: str
    target_id: int
    details: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True
