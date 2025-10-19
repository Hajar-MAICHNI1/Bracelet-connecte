from __future__ import annotations
from pydantic import BaseModel, ConfigDict
from typing import Optional, List
import uuid
from datetime import datetime

# Shared properties
class DeviceBase(BaseModel):
    serial_number: Optional[str] = None
    model: Optional[str] = None
    firmware_version: Optional[str] = None
    is_active: Optional[bool] = True
    registered_at: Optional[datetime] = None

# Properties to receive via API on creation
class DeviceCreate(DeviceBase):
    serial_number: str
    model: str
    firmware_version: str

# Properties to receive via API on update
class DeviceUpdate(DeviceBase):
    pass

# Properties shared by models in DB
class DeviceInDBBase(DeviceBase):
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

# Properties to return to client
class Device(DeviceInDBBase):
    metrics: List["Metric"] = []