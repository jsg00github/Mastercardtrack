"""
Authentication system with JWT tokens
"""
import os
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from sqlalchemy import or_
from . import models, schemas
from .database import get_db

# Security configuration
SECRET_KEY = os.getenv("SECRET_KEY", "cardtrack-super-secret-key-change-in-production-2024")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Bearer token security
security = HTTPBearer()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT token"""
    try:
        print(f"[DECODE] Attempting to decode token with SECRET_KEY: {SECRET_KEY[:20]}...")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        print(f"[DECODE] Success: {payload}")
        return payload
    except JWTError as e:
        print(f"[DECODE] JWTError: {e}")
        return None
    except Exception as e:
        print(f"[DECODE] Unexpected error: {e}")
        return None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> models.User:
    """Get the current authenticated user from JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token = credentials.credentials
    print(f"[AUTH] Token received: {token[:50]}..." if token else "[AUTH] No token")
    
    payload = decode_token(token)
    print(f"[AUTH] Payload decoded: {payload}")
    
    if payload is None:
        print("[AUTH] FAIL: payload is None")
        raise credentials_exception
    
    user_id_str = payload.get("sub")
    print(f"[AUTH] User ID from payload: {user_id_str} (type: {type(user_id_str)})")
    
    if user_id_str is None:
        print("[AUTH] FAIL: user_id is None")
        raise credentials_exception
    
    try:
        user_id = int(user_id_str)  # Convert back to int
    except (ValueError, TypeError):
        print(f"[AUTH] FAIL: Cannot convert user_id to int: {user_id_str}")
        raise credentials_exception
    
    user = db.query(models.User).filter(models.User.id == user_id).first()
    print(f"[AUTH] User found: {user}")
    
    if user is None:
        print("[AUTH] FAIL: user not found in DB")
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario desactivado"
        )
    
    print(f"[AUTH] SUCCESS: User {user.username} authenticated")
    return user


def register_user(db: Session, user_data: schemas.UserCreate) -> models.User:
    """Register a new user"""
    try:
        # Check if email already exists
        if db.query(models.User).filter(models.User.email == user_data.email).first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El email ya está registrado"
            )
        
        # Check if username already exists
        if db.query(models.User).filter(models.User.username == user_data.username).first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El nombre de usuario ya existe"
            )
        
        # Create user
        hashed_password = get_password_hash(user_data.password)
        db_user = models.User(
            email=user_data.email,
            username=user_data.username,
            hashed_password=hashed_password
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        # Create default categories for the user
        for cat_data in models.DEFAULT_CATEGORIES:
            category = models.Category(
                user_id=db_user.id,
                name=cat_data["name"],
                icon=cat_data["icon"],
                color=cat_data["color"],
                is_default=True
            )
            db.add(category)
        db.commit()
        
        return db_user
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[REGISTER ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno durante registro: {str(e)}"
        )


def authenticate_user(db: Session, username: str, password: str) -> Optional[models.User]:
    """Authenticate a user by username or email and password"""
    user = db.query(models.User).filter(
        or_(
            models.User.username == username,
            models.User.email == username
        )
    ).first()
    
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user



def create_user_token(user: models.User) -> schemas.Token:
    """Create a token response for a user"""
    access_token = create_access_token(data={"sub": str(user.id)})  # Convert to string!
    return schemas.Token(
        access_token=access_token,
        token_type="bearer",
        user=schemas.UserResponse.model_validate(user)
    )
