from sqlalchemy.orm import Session
from app.models.device import Device
from app.schemas.device import DeviceCreate
from app.repositories.base import BaseRepository

class DeviceRepository(BaseRepository[Device]):
    def get_by_api_key(self, db: Session, *, api_key: str) -> Device | None:
        return db.query(Device).filter(Device.api_key == api_key).first()

    def get_by_serial_number(self, db: Session, *, serial_number: str) -> Device | None:
        return db.query(Device).filter(Device.serial_number == serial_number).first()

    def create(self, db: Session, *, obj_in: DeviceCreate) -> Device:
        db_obj = Device(
            name=obj_in.name,
            serial_number=obj_in.serial_number,
            api_key=obj_in.api_key,
            user_id=obj_in.user_id,
            registered_at=obj_in.registered_at
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

device_repository = DeviceRepository(Device)
