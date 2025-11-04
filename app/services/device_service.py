from sqlalchemy.orm import Session
from app.models.user import User
from app.schemas.device import DeviceRegister, DeviceCreate
from app.repositories.device_repository import device_repository
from app.core.security import generate_api_key
from datetime import datetime
from app.core.exceptions import DeviceAlreadyExistsException

class DeviceService:
    def register_device(self, db: Session, *, user: User, device_in: DeviceRegister) -> dict:
        existing_device = device_repository.get_by_serial_number(db, serial_number=device_in.serial_number)
        if existing_device:
            raise DeviceAlreadyExistsException(serial_number=device_in.serial_number)

        api_key = generate_api_key()
        device_create = DeviceCreate(
            name=device_in.name,
            serial_number=device_in.serial_number,
            api_key=api_key,
            user_id=user.id,
            registered_at=datetime.utcnow()
        )
        device = device_repository.create(db, obj_in=device_create)
        return {"api_key": api_key, "device": device}

device_service = DeviceService()
