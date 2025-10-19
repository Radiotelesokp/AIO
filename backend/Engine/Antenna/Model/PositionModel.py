from pydantic import BaseModel


# Klasa reprezentująca pozycję anteny
class PositionModel(BaseModel):
    """Model pozycji anteny"""
    azimuth: float
    elevation: float