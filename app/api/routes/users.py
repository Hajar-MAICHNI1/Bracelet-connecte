from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from app.api import deps
from app.schemas.user import User, UserCreate, UserUpdate
from app.services.user_service import user_service
from pydantic import BaseModel, EmailStr
from uuid import UUID

router = APIRouter()

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

@router.post("/users/", response_model=User)
def create_user(
    *, 
    db: Session = Depends(deps.get_db), 
    user_in: UserCreate
):
    """
    Create new user.
    """
    user = user_service.get_by_email(db, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this username already exists in the system.",
        )
    user = user_service.create_user(db, user_in=user_in)
    return user

@router.get("/users/", response_model=list[User])
def read_users(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
):
    """
    Retrieve users.
    """
    users = user_service.get_multi(db, skip=skip, limit=limit)
    return users

@router.get("/users/{user_id}", response_model=User)
def read_user_by_id(
    user_id: UUID,
    db: Session = Depends(deps.get_db),
):
    """
    Get a specific user by ID.
    """
    user = user_service.get(db, id=str(user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.put("/users/{user_id}", response_model=User)
def update_user(
    *,
    db: Session = Depends(deps.get_db),
    user_id: UUID,
    user_in: UserUpdate,
):
    """
    Update a user.
    """
    user = user_service.get(db, id=str(user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user = user_service.update_user(db, db_obj=user, obj_in=user_in)
    return user

@router.delete("/users/{user_id}", response_model=User)
def delete_user(
    *,
    db: Session = Depends(deps.get_db),
    user_id: UUID,
):
    """
    Delete a user (soft delete).
    """
    user = user_service.delete_user(db, id=str(user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.get("/users/verify-email", response_model=User)
def verify_email(
    *, 
    db: Session = Depends(deps.get_db), 
    token: str
):
    """
    Verify user email.
    """
    user = user_service.verify_email(db, token=token)
    if not user:
        raise HTTPException(
            status_code=400, 
            detail="Invalid or expired token"
        )
    return user

@router.post("/users/forgot-password")
def forgot_password(
    *, 
    db: Session = Depends(deps.get_db), 
    request: ForgotPasswordRequest
):
    """
    Send password reset email.
    """
    user = user_service.get_by_email(db, email=request.email)
    if user:
        user_service.send_password_reset_email(user)
    return {"message": "If a user with that email exists, a password reset email has been sent."}

@router.post("/users/reset-password", response_model=User)
def reset_password(
    *, 
    db: Session = Depends(deps.get_db), 
    request: ResetPasswordRequest
):
    """
    Reset user password.
    """
    user = user_service.reset_password(
        db, token=request.token, new_password=request.new_password
    )
    if not user:
        raise HTTPException(
            status_code=400, 
            detail="Invalid or expired token"
        )
    return user