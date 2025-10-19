from typing import Optional
from pydantic import BaseModel, Field
from backend.Engine.Antenna.Model import ObserverLocationModel
from backend.Engine.Antenna.Model.PositionModel import PositionModel


class StatusResponse(BaseModel):
    """Odpowiedź statusu anteny"""
    connected: bool
    current_position: Optional[PositionModel]
    is_moving: bool
    last_error: Optional[str]
    observer_location: Optional[ObserverLocationModel]
    port: Optional[str] = Field(None, description="Aktualnie używany port szeregowy")