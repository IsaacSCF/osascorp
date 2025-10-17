from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.users import User
from app.schemas.users import UserCreate, UserLogin, UserResponse, Token, UserUpdate, UserApproval, UserListResponse
from app.utils.security import hash_password, verify_password, validate_email, validate_username, sanitize_input
from app.utils.auth import create_access_token, get_current_active_user, check_role
from datetime import datetime, timedelta
import json

router = APIRouter()

# Armazenamento temporário para tentativas de login (em produção, use Redis)
login_attempts = {}
blocked_users = {}

@router.post("/register", response_model=UserResponse)
def register(user: UserCreate, db: Session = Depends(get_db)):
    # Validate input
    if not validate_username(user.username):
        raise HTTPException(status_code=400, detail="Invalid username")
    if not validate_email(user.email):
        raise HTTPException(status_code=400, detail="Invalid email")

    # Sanitize inputs
    user.username = sanitize_input(user.username)
    user.email = sanitize_input(user.email)

    # Check if user exists
    db_user = db.query(User).filter(
        (User.username == user.username) | (User.email == user.email)
    ).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username or email already registered")

    # Create user
    hashed_password = hash_password(user.password)
    db_user = User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password,
        role=user.role
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@router.post("/login", response_model=Token)
def login(user_credentials: UserLogin, db: Session = Depends(get_db)):
    username = user_credentials.username
    current_time = datetime.now()

    # Verificar se usuário está bloqueado
    if username in blocked_users:
        block_time = blocked_users[username]
        if current_time < block_time:
            remaining_time = int((block_time - current_time).total_seconds())
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Account temporarily blocked. Try again in {remaining_time} seconds.",
            )
        else:
            # Remover bloqueio expirado
            del blocked_users[username]
            if username in login_attempts:
                del login_attempts[username]

    # Verificar credenciais
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(user_credentials.password, user.hashed_password):
        # Incrementar tentativas de login
        if username not in login_attempts:
            login_attempts[username] = 0
        login_attempts[username] += 1

        # Bloquear após 5 tentativas
        if login_attempts[username] >= 5:
            blocked_users[username] = current_time + timedelta(minutes=5)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many failed attempts. Account blocked for 5 minutes.",
            )

        attempts_left = 5 - login_attempts[username]
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Incorrect username or password. {attempts_left} attempts remaining.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Login bem-sucedido - limpar tentativas
    if username in login_attempts:
        del login_attempts[username]
    if username in blocked_users:
        del blocked_users[username]

    # Gerar token com expiração baseada em "remember me" (simulado)
    # Em produção, o frontend enviaria essa informação
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserResponse)
def read_users_me(current_user: User = Depends(get_current_active_user)):
    return current_user

@router.get("/pending", response_model=list[UserListResponse])
def get_pending_users(current_user: User = Depends(check_role("admin")), db: Session = Depends(get_db)):
    """List all users pending approval"""
    users = db.query(User).filter(User.status == "pendente").all()
    return users

@router.post("/{user_id}/approve", response_model=UserResponse)
def approve_user(
    user_id: int,
    approval: UserApproval,
    current_user: User = Depends(check_role("admin")),
    db: Session = Depends(get_db)
):
    """Approve or reject a user registration"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.status != "pendente":
        raise HTTPException(status_code=400, detail="User is not pending approval")

    user.status = approval.status
    user.approved_by = current_user.id
    user.approved_at = datetime.now()

    if approval.status == "aprovado":
        if approval.role:
            user.role = approval.role
        if approval.permissions:
            user.permissions = json.dumps(approval.permissions)

    db.commit()
    db.refresh(user)
    return user

@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    user_update: UserUpdate,
    current_user: User = Depends(check_role("admin")),
    db: Session = Depends(get_db)
):
    """Update user role, status, or permissions"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    update_data = user_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        if field == "permissions" and value is not None:
            value = json.dumps(value)
        setattr(user, field, value)

    db.commit()
    db.refresh(user)
    return user

@router.get("/", response_model=list[UserListResponse])
def list_users(
    skip: int = 0,
    limit: int = 100,
    status_filter: str = None,
    current_user: User = Depends(check_role("admin")),
    db: Session = Depends(get_db)
):
    """List all users with optional status filter"""
    query = db.query(User)
    if status_filter:
        query = query.filter(User.status == status_filter)
    users = query.offset(skip).limit(limit).all()
    return users

from pydantic import BaseModel

class ChangePasswordRequest(BaseModel):
    new_password: str

@router.put("/{user_id}/change-password")
def change_user_password(
    user_id: int,
    request: ChangePasswordRequest,
    current_user: User = Depends(check_role("admin")),
    db: Session = Depends(get_db)
):
    """Change a user's password (admin only)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    new_password = request.new_password

    # Validate new password
    if len(new_password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters long")

    # Hash and update password
    hashed_password = hash_password(new_password)
    user.hashed_password = hashed_password
    user.updated_at = datetime.now()

    db.commit()
    return {"message": "Password changed successfully"}

@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    current_user: User = Depends(check_role("admin")),
    db: Session = Depends(get_db)
):
    """Delete a user (admin only)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Prevent deleting admin users (make them irremovable)
    if user.role == "admin":
        raise HTTPException(status_code=400, detail="Admin users cannot be deleted")

    db.delete(user)
    db.commit()
    return {"message": "User deleted successfully"}
