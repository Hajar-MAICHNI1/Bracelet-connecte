from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api import deps
from app.models.user import User
from app.schemas.device import DeviceRegister, DeviceRegistrationResponse
from app.services.device_service import device_service

router = APIRouter()

@router.post("/devices/register", response_model=DeviceRegistrationResponse)
def register_device(
    *,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    device_in: DeviceRegister,
) -> dict:
    """
    Register a new device.
    """
    result = device_service.register_device(db, user=current_user, device_in=device_in)
    return result
