from pydantic import BaseModel, Field


class ObserverLocationModel(BaseModel):
    """Observer location model"""
    latitude: float = Field(..., ge=-90, le=90, description="Geographic latitude in degrees")
    longitude: float = Field(..., ge=-180, le=180, description="Geographic longitude in degrees")
    elevation: float = Field(0, ge=0, description="Elevation above sea level in meters")
    name: str = Field("Observer", description="Location name")
