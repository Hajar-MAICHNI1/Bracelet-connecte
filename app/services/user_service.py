from sqlalchemy.orm import Session
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.repositories.user_repository import user_repository
from app.core.security import get_password_hash, generate_verification_token, verify_verification_token, generate_password_reset_token, verify_password_reset_token
from datetime import datetime
from app.core.exceptions import UserNotFoundException, UserAlreadyExistsException
import smtplib, ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from app.config.settings import settings
from typing import List, Dict, Any

class UserService:
    def __init__(self, user_repo):
        self.user_repo = user_repo

    def get(self, db: Session, id: str) -> User | None:
        user = self.user_repo.get(db, id=id)
        if not user:
            raise UserNotFoundException(user_id=id)
        return user

    def get_multi(
        self, db: Session, *, skip: int = 0, limit: int = 100
    ) -> List[User]:
        return self.user_repo.get_multi(db, skip=skip, limit=limit)

    def create_user(self, db: Session, *, user_in: UserCreate) -> User:
        existing_user = self.get_by_email(db, email=user_in.email)
        if existing_user:
            raise UserAlreadyExistsException(email=user_in.email)
        hashed_password = get_password_hash(user_in.password)
        user_in_db = UserCreate(email=user_in.email, password=hashed_password, name=user_in.name)
        user = self.user_repo.create(db, obj_in=user_in_db)
        self.send_verification_email(user)
        return user

    def update_user(
        self, db: Session, *, db_obj: User, obj_in: UserUpdate | Dict[str, Any]
    ) -> User:
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)

        if "password" in update_data and update_data["password"]:
            hashed_password = get_password_hash(update_data["password"])
            update_data["hashed_password"] = hashed_password
            del update_data["password"]
        
        return self.user_repo.update(db, db_obj=db_obj, obj_in=update_data)

    def delete_user(self, db: Session, *, id: str) -> User | None:
        user = self.user_repo.remove(db, id=id)
        if not user:
            raise UserNotFoundException(user_id=id)
        return user

    def get_by_email(self, db: Session, *, email: str) -> User | None:
        return self.user_repo.get_by_email(db, email=email)

    def send_verification_email(self, user: User):
        token = generate_verification_token(user.email)
        
        message = MIMEMultipart("alternative")
        message["Subject"] = "Verify your email address"
        message["From"] = settings.SMTP_USER
        message["To"] = user.email

        text = f"""\
        Hi {user.name},
        Thanks for signing up to our service.
        Please verify your email address by clicking the link below:
        http://localhost:8000/api/v1/users/verify-email?token={token}
        """
        html = f"""\
        <html>
          <body>
            <p>Hi {user.name},<br>
               Thanks for signing up to our service.<br>
               Please verify your email address by clicking the link below:<br>
               <a href="http://localhost:8000/api/v1/users/verify-email?token={token}">Verify email</a> 
            </p>
          </body>
        </html>
        """

        part1 = MIMEText(text, "plain")
        part2 = MIMEText(html, "html")

        message.attach(part1)
        message.attach(part2)

        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(settings.SMTP_SERVER, settings.SMTP_PORT, context=context) as server:
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(
                settings.SMTP_USER, user.email, message.as_string()
            )


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
        
        message = MIMEMultipart("alternative")
        message["Subject"] = "Reset your password"
        message["From"] = settings.SMTP_USER
        message["To"] = user.email

        text = f"""\
        Hi {user.name},
        Please reset your password by clicking the link below:
        http://127.0.0.1:8000/api/v1/users/reset-password?token={token}
        """
        html = f"""\
        <html>
          <body>
            <p>Hi {user.name},<br>
               Please reset your password by clicking the link below:<br>
               <a href="http://127.0.0.1:8000/api/v1/users/reset-password?token={token}">Reset password</a> 
            </p>
          </body>
        </html>
        """

        part1 = MIMEText(text, "plain")
        part2 = MIMEText(html, "html")

        message.attach(part1)
        message.attach(part2)

        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(settings.SMTP_SERVER, settings.SMTP_PORT, context=context) as server:
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(
                settings.SMTP_USER, user.email, message.as_string()
            )

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