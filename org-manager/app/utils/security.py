import bcrypt
import re
from typing import Optional

def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def sanitize_input(input_str: str) -> str:
    """Sanitize user input to prevent injection attacks."""
    if not input_str:
        return input_str
    # Remove potentially dangerous characters
    sanitized = re.sub(r'[<>]', '', input_str)
    return sanitized.strip()

def validate_email(email: str) -> bool:
    """Basic email validation."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_username(username: str) -> bool:
    """Validate username (alphanumeric, underscore, dash, 3-20 chars)."""
    pattern = r'^[a-zA-Z0-9_-]{3,20}$'
    return re.match(pattern, username) is not None
