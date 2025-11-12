from typing import Optional
from pydantic import BaseModel, Field


class AzimuthCalibrationModel(BaseModel):
    """Azimuth calibration model"""
    current_azimuth: Optional[float] = Field(None, description="Current azimuth position (if None, uses the current value)")
    save_to_file: bool = Field(True, description="Whether to save the calibration to a file")
