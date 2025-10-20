from typing import Optional
from pydantic import BaseModel, Field


class ConnectionConfigModel(BaseModel):
    """Connection configuration model"""
    port: Optional[str] = Field(None, description="Serial port (auto-detect if not provided)")
    baudrate: int = Field(115200, description="Transmission speed")
    use_simulator: bool = Field(False, description="Use simulator instead of real hardware")
