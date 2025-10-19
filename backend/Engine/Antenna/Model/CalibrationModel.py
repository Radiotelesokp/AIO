from pydantic import BaseModel, Field


class CalibrationModel(BaseModel):
    """Model kalibracji anteny"""
    azimuth_offset: float = Field(0.0, description="Offset azymutu w stopniach")
    elevation_offset: float = Field(0.0, description="Offset elewacji w stopniach")