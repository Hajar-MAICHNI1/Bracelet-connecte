from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api import deps
from app.models.device import Device
from app.schemas.metric import MetricBatch
from app.services.metric_service import metric_service
from typing import List

router = APIRouter()

@router.post("/metrics/batch/", status_code=201)
def create_metrics(
    *,
    db: Session = Depends(deps.get_db),
    current_device: Device = Depends(deps.get_current_device),
    metrics_in: MetricBatch,
) -> dict:
    """
    Create new metrics for the current device.
    """
    metric_service.create_metrics(db, device=current_device, metrics_in=metrics_in)
    return {"message": "Metrics received"}
