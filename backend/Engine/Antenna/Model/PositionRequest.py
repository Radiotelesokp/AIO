from pydantic import BaseModel


# Modele Pydantic dla API
# Klasa odpowiedzialna za żądanie przeniesienia anteny w określone położenie
class PositionRequest(BaseModel):
    """Żądanie pozycji anteny"""
    azimuth: float
    elevation: float
