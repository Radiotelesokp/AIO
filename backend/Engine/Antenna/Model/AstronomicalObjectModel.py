from pydantic import BaseModel, Field
from backend.Engine.AstronomyCalculator import AstronomicalObjectType


class AstronomicalObjectModel(BaseModel):
    """Astronomical object model"""
    name: str = Field(..., description="Name of the astronomical object")
    object_type: AstronomicalObjectType = Field(..., description="Type of object")