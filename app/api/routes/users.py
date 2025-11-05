from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from app.api import deps
from app.schemas.user import User, UserCreate, UserUpdate, UserVerifyEmail, ResetPasswordWithCodeRequest
from app.services.user_service import user_service
from pydantic import BaseModel, EmailStr
from uuid import UUID

router = APIRouter()

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

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

@router.post("/users/verify-email", response_model=User)
def verify_email(
    *, 
    db: Session = Depends(deps.get_db), 
    request: UserVerifyEmail
):
    """
    Verify user email with a 6-digit code.
    """
    user = user_service.verify_email_with_code(db, email=request.email, code=request.code)
    return user

@router.post("/users/forgot-password")
def forgot_password(
    *, 
    db: Session = Depends(deps.get_db), 
    request: ForgotPasswordRequest
):
    """
    Send password reset code.
    """
    user_service.initiate_password_reset(db, email=request.email)
    return {"message": "If a user with that email exists, a password reset code has been sent."}

@router.post("/users/reset-password", response_model=User)
def reset_password(
    *, 
    db: Session = Depends(deps.get_db), 
    request: ResetPasswordWithCodeRequest
):
    """
    Reset user password with a 6-digit code.
    """
    user = user_service.reset_password_with_code(
        db, email=request.email, code=request.code, new_password=request.new_password
    )
    return user