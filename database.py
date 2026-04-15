import datetime as dt
import os
from sqlalchemy import Boolean, Column, DateTime, Integer, String, create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

# Use environment variable for database URL, default to local SQLite
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./appointments_db.db")

# SQLite requires 'check_same_thread': False
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


Base = declarative_base()

class Appointment(Base):
    __tablename__ = "appointments"
    id = Column(Integer, primary_key=True, index=True)
    patient_name = Column(String, index=True)
    patient_phone = Column(String, index=True)
    purpose = Column(String, nullable=False)
    patient_age = Column(String)
    patient_gender = Column(String)
    date = Column(String, nullable=False)
    token_number = Column(Integer, nullable=False)
    canceled = Column(Boolean, default=False)
    created_at = Column(DateTime, default=dt.datetime.utcnow)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()

#init_db()