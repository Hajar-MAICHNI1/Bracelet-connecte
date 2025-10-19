from app.core.database import Base, engine
from app.models.user import User
from app.models.device import Device
from app.models.metric import Metric

print("Dropping all tables...")
Base.metadata.drop_all(bind=engine)
print("Tables dropped successfully.")

print("Creating database tables...")
Base.metadata.create_all(bind=engine)
print("Tables created successfully.")