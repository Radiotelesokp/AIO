from typing import Optional
from pydantic import BaseModel, Field


class AzimuthCalibrationModel(BaseModel):
    """Model kalibracji azymutu"""
    current_azimuth: Optional[float] = Field(
        None, description="Aktualna pozycja azymutu (jeśli None, użyje aktualnej)"
    )
    save_to_file: bool = Field(True, description="Czy zapisać kalibrację do pliku")