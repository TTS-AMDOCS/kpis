"""Domain models"""

from pydantic import BaseModel
from datetime import datetime


class KPIBase(BaseModel):
    """Model for the kpis"""
    kpi_id: int
    kpi_name: str
    timestamp: datetime
    value: float


class KPICreate(KPIBase):
    """Model for KPI creation"""
    pass


class AlertBase(BaseModel):
    """Model for the alerts"""
    alert_id: int
    timestamp: datetime
    message: str


class AlertCreate(AlertBase):
    """Model for alerts creation"""
    pass
