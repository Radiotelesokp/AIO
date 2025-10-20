from pydantic import BaseModel


# Klasa reprezentująca pozycję anteny
class PositionModel(BaseModel):
    """Antenna position model"""
    azimuth: float
    elevation: float