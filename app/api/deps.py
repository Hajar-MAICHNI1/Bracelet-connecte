from app.services.blacklist_service import blacklist_service
from app.core.database import get_db
from typing import Generator
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, exceptions
from pydantic import ValidationError
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.schemas.token import TokenPayload
from app.models.user import User
from app.models.device import Device
from app.services.user_service import UserService
from app.config.settings import settings

security_scheme = HTTPBearer()


def get_current_user(
    db: Session = Depends(get_db), 
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme)
) -> User:
    token = credentials.credentials
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        token_data = TokenPayload(**payload)
    except (exceptions.JWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )
    
    if token_data.jti and blacklist_service.is_blacklisted(token_data.jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
        )

    if token_data.sub is None:
        raise HTTPException(status_code=404, detail="User not found")

    user_service = UserService(db)
    user = user_service.get_user_by_id(token_data.sub)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user

def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    # if not crud.user.is_active(current_user):
    #     raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

def get_current_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user

