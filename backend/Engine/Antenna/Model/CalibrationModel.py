from pydantic import BaseModel, Field


class CalibrationModel(BaseModel):
    """Antenna calibration model"""
    azimuth_offset: float = Field(0.0, description="Azimuth offset in degrees")
    elevation_offset: float = Field(0.0, description="Elevation offset in degrees")
