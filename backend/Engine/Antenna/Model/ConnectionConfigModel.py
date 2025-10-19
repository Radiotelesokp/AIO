from typing import Optional
from pydantic import BaseModel, Field


class ConnectionConfigModel(BaseModel):
    """Model konfiguracji połączenia"""
    port: Optional[str] = Field(None, description="Port szeregowy (auto-detect jeśli nie podano)")
    baudrate: int = Field(115200, description="Prędkość transmisji")
    use_simulator: bool = Field(False, description="Użyj symulatora zamiast prawdziwego sprzętu")