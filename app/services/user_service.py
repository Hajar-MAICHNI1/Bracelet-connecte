from sqlalchemy.orm import Session
from app.models.user import User
from app.schemas.user import UserCreate
from app.repositories.user_repository import user_repository
from app.core.security import get_password_hash, generate_verification_token, verify_verification_token, generate_password_reset_token, verify_password_reset_token
from datetime import datetime

class UserService:
    def __init__(self, user_repo):
        self.user_repo = user_repo

    def create_user(self, db: Session, *, user_in: UserCreate) -> User:
        hashed_password = get_password_hash(user_in.password)
        user_in_db = UserCreate(email=user_in.email, password=hashed_password, name=user_in.name)
        user = self.user_repo.create(db, obj_in=user_in_db)
        self.send_verification_email(user)
        return user

    def get_by_email(self, db: Session, *, email: str) -> User | None:
        return self.user_repo.get_by_email(db, email=email)

    def send_verification_email(self, user: User):
        token = generate_verification_token(user.email)
        # In a real app, you would send this token in an email
        print(f"Verification token for {user.email}: {token}")

    def verify_email(self, db: Session, *, token: str) -> User | None:
        email = verify_verification_token(token)
        if not email:
            return None
        user = self.get_by_email(db, email=email)
        if not user or user.email_verified_at:
            return None
        user.email_verified_at = datetime.utcnow()
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    def send_password_reset_email(self, user: User):
        token = generate_password_reset_token(user.email)
        # In a real app, you would send this token in an email
        print(f"Password reset token for {user.email}: {token}")

    def reset_password(self, db: Session, *, token: str, new_password: str) -> User | None:
        email = verify_password_reset_token(token)
        if not email:
            return None
        user = self.get_by_email(db, email=email)
        if not user:
            return None
        hashed_password = get_password_hash(new_password)
        user.hashed_password = hashed_password
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

user_service = UserService(user_repository)