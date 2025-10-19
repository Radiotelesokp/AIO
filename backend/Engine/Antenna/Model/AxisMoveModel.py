from pydantic import BaseModel, Field

class AxisMoveModel(BaseModel):
    """Model ruchu osi anteny"""
    axis: str = Field(..., description="Oś do ruchu: 'azimuth' lub 'elevation'")
    direction: str = Field(..., description="Kierunek: 'positive' lub 'negative'")
    amount: float = Field(1.0, description="Wielkość ruchu w stopniach")