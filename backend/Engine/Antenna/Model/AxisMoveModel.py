from pydantic import BaseModel, Field

class AxisMoveModel(BaseModel):
    """Antenna axis movement model"""
    axis: str = Field(..., description="Axis to move: 'azimuth' or 'elevation'")
    direction: str = Field(..., description="Direction: 'positive' or 'negative'")
    amount: float = Field(1.0, description="Movement amount in degrees")