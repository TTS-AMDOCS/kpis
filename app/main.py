from typing import List, Dict

from fastapi import Depends, HTTPException, FastAPI
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from random import uniform
from datetime import datetime, timedelta

from models import KPIBase, KPICreate, AlertBase, AlertCreate


app = FastAPI()

SQLALCHEMY_DATABASE_URL = ("mysql+pymysql://root:admin@mysql_container:3306"
                           "/network_insights")

engine = create_engine(SQLALCHEMY_DATABASE_URL)

SessionLocal = sessionmaker(bind=engine)

Base = declarative_base()

KPI_NAMES = {
    1: "Network Uptime",
    2: "Call Completion Rate",
    3: "Network Latency",
    4: "Throughput",
    5: "Packet Loss Rate"
}


def create_sample_kpis_and_alerts(db: Session) -> None:
    """Generate sample KPIs and alerts data for a month (30 days).

    This function creates sample KPI and alert data for a period of 30 days, starting
    from 29 days ago up to the current time. It generates random values for each KPI
    and checks if any alert needs to be raised based on predefined thresholds.

    :param db: Database session.

    :return: None
    """
    start_time = datetime.utcnow() - timedelta(days=29)
    end_time = datetime.utcnow()
    delta = timedelta(hours=1)

    kpis = []
    alerts = []
    current_time = start_time
    while current_time <= end_time:
        for kpi_id, kpi_name in KPI_NAMES.items():
            value = round(uniform(90, 100), 2)
            kpi = KPI(kpi_id=kpi_id, kpi_name=kpi_name, timestamp=current_time,
                      value=value)
            kpis.append(kpi)

            if kpi_id == 1 and value < 95:
                alert_message = f"Network uptime fell below 95% at {current_time}"
                alert = Alert(alert_id=kpi_id, timestamp=current_time,
                              message=alert_message)
                alerts.append(alert)
            elif kpi_id == 2 and value < 98:
                alert_message = f"Call completion rate fell below 98% at {current_time}"
                alert = Alert(alert_id=kpi_id, timestamp=current_time,
                              message=alert_message)
                alerts.append(alert)
        current_time += delta
    db.add_all(kpis)
    db.add_all(alerts)
    db.commit()


@app.on_event("startup")
async def startup_event() -> None:
    """Perform startup tasks such as creating tables and inserting sample data.

    This function is called when the FastAPI application starts up. It ensures that
    necessary database tables are created if they don't exist already, and inserts
    sample KPIs and alerts data if the tables are empty.

    :return: None

    """
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    if not db.query(KPI).first() and not db.query(Alert).first():
        create_sample_kpis_and_alerts(db)
    db.close()


class User(Base):
    """User Model"""
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(255), unique=True, index=True)
    email = Column(String(255), unique=True, index=True)
    password = Column(String(255))


class KPI(Base):
    """KPIs Model"""
    __tablename__ = "kpis"
    id = Column(Integer, primary_key=True, index=True)
    kpi_id = Column(Integer, index=True)
    kpi_name = Column(String(255))  # New column for KPI names
    timestamp = Column(DateTime, default=datetime.utcnow)
    value = Column(Float)


class Alert(Base):
    """Alerts Model"""
    __tablename__ = "alerts"
    id = Column(Integer, primary_key=True, index=True)
    alert_id = Column(Integer, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    message = Column(String(255))


def get_db() -> Session:
    """Get a database session.

    This function is used as a dependency to provide a database session to other
    functions.
    The session is retrieved from the SessionLocal object, and it is closed
    automatically after its use.

    :return: Database session.
    :rtype: Session.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/kpis", response_model=List[KPIBase])
async def read_kpis(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)) ->\
        List[dict]:
    """Retrieve all KPIs.

    :param skip: Number of records to skip (default is 0).
    :param limit: Maximum number of records to return (default is 10).
    :param db: Database session dependency.

    :return: List of KPIs.
    :return: List[dict]
    """
    return db.query(KPI).offset(skip).limit(limit).all()


@app.get("/kpis/{kpi_id}", response_model=KPIBase)
async def read_kpi(kpi_id: int, db: Session = Depends(get_db)) -> dict:
    """Retrieve a specific KPI by ID.

    :param kpi_id: The ID of the KPI to retrieve.
    :param db: Database session dependency.

    :return: The requested KPI.
    :rtype: dict
    """
    kpi = db.query(KPI).filter(KPI.id == kpi_id).first()
    if not kpi:
        raise HTTPException(status_code=404, detail="KPI not found")
    return kpi


@app.post("/kpis", response_model=KPIBase)
async def create_kpi(kpi: KPICreate, db: Session = Depends(get_db)) -> dict:
    """Create a new KPI.

    :param kpi: Data for creating the new KPI.
    :param db: Database session dependency.

    :return: The created KPI.
    :rtype: dict
    """
    db_kpi = KPI(**kpi.dict())
    db.add(db_kpi)
    db.commit()
    db.refresh(db_kpi)
    return db_kpi


@app.put("/kpis/{kpi_id}", response_model=KPIBase)
async def update_kpi(kpi_id: int, kpi: KPICreate, db: Session = Depends(get_db)) -> \
        dict:
    """
    Update an existing KPI by ID.

    :param kpi_id: The ID of the KPI to update.
    :param kpi: Data for updating the KPI.
    :param db: Database session dependency.

    :return: The updated KPI.
    :rtype: dict
    """
    db_kpi = db.query(KPI).filter(KPI.id == kpi_id).first()
    if not db_kpi:
        raise HTTPException(status_code=404, detail="KPI not found")
    update_data = kpi.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_kpi, key, value)
    db.commit()
    db.refresh(db_kpi)
    return db_kpi


@app.delete("/kpis/{kpi_id}")
async def delete_kpi(kpi_id: int, db: Session = Depends(get_db)) -> Dict[str, str]:
    """
    Delete a KPI by ID.

    :param kpi_id: The ID of the KPI to delete.
    :param db: Database session dependency.

    :return: A message indicating the success of the deletion.
    :rtype: dict
    """
    kpi = db.query(KPI).filter(KPI.id == kpi_id).first()
    if not kpi:
        raise HTTPException(status_code=404, detail="KPI not found")
    db.delete(kpi)
    db.commit()
    return {"message": "KPI deleted successfully"}


@app.get("/alerts", response_model=List[AlertBase])
async def read_alerts(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)) \
        -> List[dict]:
    """
    Retrieve all alerts.

    :param skip: Number of records to skip (default is 0).
    :param limit: Maximum number of records to return (default is 10).
    :param db: Database session dependency.

    :return: List of alerts.
    :rtype: List[dict]
    """
    return db.query(Alert).offset(skip).limit(limit).all()


@app.get("/alerts/{alert_id}", response_model=AlertBase)
async def read_alert(alert_id: int, db: Session = Depends(get_db)) -> dict:
    """
    Retrieve a specific alert by ID.

    :param alert_id: The ID of the alert to retrieve.
    :param db: Database session dependency.

    :return: The requested alert.
    :return: dict
    """
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert


@app.post("/alerts", response_model=AlertBase)
async def create_alert(alert: AlertCreate, db: Session = Depends(get_db)) -> dict:
    """Create a new alert.

    :param alert: Data for creating the new alert.
    :param db: Database session dependency.

    :return: The created alert.
    :rtype: dict
    """
    db_alert = Alert(**alert.dict())
    db.add(db_alert)
    db.commit()
    db.refresh(db_alert)
    return db_alert


@app.put("/alerts/{alert_id}", response_model=AlertBase)
async def update_alert(alert_id: int, alert: AlertCreate,
                       db: Session = Depends(get_db)) -> dict:
    """
    Update an existing alert by ID.

    :param alert_id: The ID of the alert to update.
    :param alert: Data for updating the alert.
    :param db: Database session dependency.

    :return: The updated alert.
    :rtype: dict
    """
    db_alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not db_alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    update_data = alert.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_alert, key, value)
    db.commit()
    db.refresh(db_alert)
    return db_alert


@app.delete("/alerts/{alert_id}")
async def delete_alert(alert_id: int, db: Session = Depends(get_db)) -> Dict[str, str]:
    """
    Delete an alert by ID.

    :param alert_id: The ID of the alert to delete.
    :param db: Database session dependency.

    :return: A message indicating the success of the deletion.
    :rtype: dict
    """
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    db.delete(alert)
    db.commit()
    return {"message": "Alert deleted successfully"}
