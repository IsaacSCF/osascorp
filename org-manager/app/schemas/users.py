from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List, Dict

class UserBase(BaseModel):
    username: str
    email: str

class UserCreate(UserBase):
    password: str
    role: Optional[str] = "visualizador"

class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(UserBase):
    id: int
    role: str
    status: str
    permissions: Optional[Dict] = None
    approved_by: Optional[int] = None
    approved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    role: Optional[str] = None
    status: Optional[str] = None
    permissions: Optional[Dict] = None

class UserApproval(BaseModel):
    status: str  # "aprovado" or "rejeitado"
    role: Optional[str] = None
    permissions: Optional[Dict] = None

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class UserListResponse(BaseModel):
    id: int
    username: str
    email: str
    role: str
    status: str
    created_at: datetime
    approved_at: Optional[datetime] = None

    class Config:
        from_attributes = True
