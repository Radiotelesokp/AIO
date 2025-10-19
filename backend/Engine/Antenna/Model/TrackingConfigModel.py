from pydantic import BaseModel, Field
from backend.Engine.AstronomyCalculator import AstronomicalObjectType


class TrackingConfigModel(BaseModel):
    """Konfiguracja śledzenia astronomicznego"""
    object_name: str = Field(..., description="Nazwa obiektu do śledzenia")
    object_type: AstronomicalObjectType = Field(
        AstronomicalObjectType.SUN, description="Typ obiektu astronomicznego"
    )
    update_interval: float = Field(
        1.0, ge=0.1, le=300, description="Interwał aktualizacji pozycji w sekundach"
    )