from pydantic import BaseModel, ConfigDict
from typing import Optional
import uuid
from datetime import datetime
from app.models.enums import MetricType

# Shared properties
class MetricBase(BaseModel):
    metric_type: Optional[MetricType] = None
    value: Optional[float] = None
    unit: Optional[str] = None
    sensor_model: Optional[str] = None
    timestamp: Optional[datetime] = None
    x: Optional[float] = None
    y: Optional[float] = None
    z: Optional[float] = None

# Properties to receive via API on creation
class MetricCreate(MetricBase):
    metric_type: MetricType
    timestamp: datetime

# Properties to receive via API on update
class MetricUpdate(MetricBase):
    pass

# Properties shared by models in DB
class MetricInDBBase(MetricBase):
    id: uuid.UUID
    user_id: uuid.UUID
    device_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

# Properties to return to client
class Metric(MetricInDBBase):
    pass