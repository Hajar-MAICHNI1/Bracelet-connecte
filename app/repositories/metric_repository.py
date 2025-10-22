from sqlalchemy.orm import Session
from app.models.metric import Metric
from app.schemas.metric import MetricCreate
from app.repositories.base import BaseRepository
from typing import List

class MetricRepository(BaseRepository[Metric]):
    def create(self, db: Session, *, obj_in: MetricCreate) -> Metric:
        db_obj = Metric(**obj_in.dict())
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def create_many(self, db: Session, *, objs_in: List[MetricCreate]) -> List[Metric]:
        db_objs = [Metric(**obj_in.dict()) for obj_in in objs_in]
        db.add_all(db_objs)
        db.commit()
        # We can't refresh multiple objects, so we just return them without the db-generated values
        return db_objs


metric_repository = MetricRepository(Metric)
