import os
import jwt
import bcrypt
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Request, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv

load_dotenv()

JWT_SECRET = os.getenv("JWT_SECRET", "fallback-secret-for-testing")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

security_scheme = HTTPBearer(auto_error=False)

def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.
    """
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")

def verify_password(password: str, hashed_password: str) -> bool:
    """
    Verify a password against its bcrypt hash.
    """
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False

def create_access_token(user_id: int, username: str, role: str) -> str:
    """
    Generate a JWT token with user claims.
    """
    expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    payload = {
        "exp": expire,
        "iat": datetime.utcnow(),
        "user_id": user_id,
        "username": username,
        "role": role
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

async def get_current_user(request: Request, credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme)) -> dict:
    """
    FastAPI dependency that extracts and validates JWT from HTTP Authorization header.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization token"
        )
        
    token = credentials.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("user_id")
        username = payload.get("username")
        role = payload.get("role")
        
        if not user_id or not username or not role:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
            
        # Bind user metadata to request state for rate limiting and logging
        request.state.user_id = user_id
        request.state.username = username
        request.state.role = role
        
        return {
            "id": user_id,
            "username": username,
            "role": role
        }
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired. Please log in again."
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid security token."
        )

def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    """
    Dependency requiring that the authenticated user holds the Admin role.
    """
    if current_user.get("role") != "Admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access required."
        )
    return current_user
