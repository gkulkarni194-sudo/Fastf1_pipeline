"""Metadata service for the API."""
from __future__ import annotations

from fastapi import HTTPException

from fastapi import HTTPException


class MetadataService:
    def __init__(self):
        # Data is mocked for the API contract
        pass
        
    def get_seasons(self) -> list[int]:
        # Typically from a select distinct season query
        try:
            return [2023, 2024] # Mocked until repo supports distinct
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Database error: {e}")
            
    def get_events(self, season: int) -> list[str]:
        # Mocked until repo supports distinct
        return ["Bahrain", "Saudi Arabia", "Australia"]
        
    def get_sessions(self, season: int, event: str) -> list[str]:
        return ["FP1", "FP2", "FP3", "Q", "R"]
        
    def get_drivers(self, season: int, event: str) -> list[str]:
        return ["VER", "PER", "HAM", "RUS", "LEC", "SAI", "NOR", "PIA", "ALO", "STR"]
