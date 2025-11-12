from pydantic import BaseModel


# Modele Pydantic dla API
# Klasa odpowiedzialna za żądanie przeniesienia anteny w określone położenie
class PositionRequest(BaseModel):
    """Antenna position request"""
    azimuth: float
    elevation: float
