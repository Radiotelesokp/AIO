from pydantic import BaseModel, Field
from backend.Engine.AstronomyCalculator import AstronomicalObjectType


class AstronomicalObjectModel(BaseModel):
    """Model obiektu astronomicznego"""
    name: str = Field(..., description="Nazwa obiektu astronomicznego")
    object_type: AstronomicalObjectType = Field(..., description="Typ obiektu")