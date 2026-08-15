"""Metadata and data schemas."""
from __future__ import annotations

from pydantic import BaseModel


class EventBase(BaseModel):
    season: int
    event: str
    
class SessionBase(EventBase):
    session: str

class DriverBase(SessionBase):
    driver: str


class DataSummaryResponse(BaseModel):
    season: int
    event: str
    session: str
    driver: str
    
    telemetry_available: bool = False
    telemetry_rows: int = 0
    laps_available: bool = False
    laps_count: int = 0
    weather_available: bool = False
