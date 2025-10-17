from datetime import datetime, timedelta
from typing import Optional
import jwt
import os
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.users import User
from app.schemas.users import TokenData

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-jwt-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

security = HTTPBearer()

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        token_data = TokenData(username=username)
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return token_data

def get_current_user(token_data: TokenData = Depends(verify_token), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == token_data.username).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user

def get_current_active_user(current_user: User = Depends(get_current_user)):
    return current_user

def check_role(required_role: str):
    def role_checker(current_user: User = Depends(get_current_active_user)):
        # Check if user is approved
        if current_user.status != "aprovado":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account not approved. Please wait for admin approval."
            )

        roles_hierarchy = {
            "visualizador": 1,
            "moderador_legal": 2,
            "moderador_ilegal": 2,
            "admin": 3
        }
        if roles_hierarchy.get(current_user.role, 0) < roles_hierarchy.get(required_role, 0):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required: {required_role}, Current: {current_user.role}"
            )
        return current_user
    return role_checker

def check_permission(permission: str):
    def permission_checker(current_user: User = Depends(get_current_active_user)):
        # Check if user is approved
        if current_user.status != "aprovado":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account not approved. Please wait for admin approval."
            )

        # Admin has all permissions
        if current_user.role == "admin":
            return current_user

        # Check specific permissions
        if current_user.permissions:
            try:
                import json
                perms = json.loads(current_user.permissions)
                if permission in perms.get("allowed", []):
                    return current_user
            except:
                pass

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission denied: {permission}"
        )
    return permission_checker

def check_org_type_access(org_type: str):
    def type_checker(current_user: User = Depends(get_current_active_user)):
        # Check if user is approved
        if current_user.status != "aprovado":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account not approved. Please wait for admin approval."
            )

        # Admin can access everything
        if current_user.role == "admin":
            return current_user

        # Moderador_legal can only access LEGAL orgs
        if current_user.role == "moderador_legal" and org_type != "LEGAL":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only manage LEGAL organizations"
            )

        # Moderador_ilegal can only access ILEGAL orgs
        if current_user.role == "moderador_ilegal" and org_type != "ILEGAL":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only manage ILEGAL organizations"
            )

        return current_user
    return type_checker
