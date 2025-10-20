from pydantic import BaseModel, Field
from backend.Engine.AstronomyCalculator import AstronomicalObjectType


class TrackingConfigModel(BaseModel):
    """Astronomical tracking configuration"""
    object_name: str = Field(..., description="Name of the object to track")
    object_type: AstronomicalObjectType = Field(AstronomicalObjectType.SUN, description="Type of astronomical object")
    update_interval: float = Field(1.0, ge=0.1, le=300, description="Position update interval in seconds")