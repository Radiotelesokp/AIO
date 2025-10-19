from pydantic import BaseModel, Field


class ObserverLocationModel(BaseModel):
    """Model lokalizacji obserwatora"""
    latitude: float = Field(..., ge=-90, le=90, description="Szerokość geograficzna w stopniach")
    longitude: float = Field(..., ge=-180, le=180, description="Długość geograficzna w stopniach")
    elevation: float = Field(0, ge=0, description="Wysokość n.p.m. w metrach")
    name: str = Field("Observer", description="Nazwa lokalizacji")