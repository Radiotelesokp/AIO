import ephem
from dataclasses import dataclass

@dataclass
class ObserverLocation:
    """Lokalizacja obserwatora"""

    latitude: float  # Szerokość geograficzna w stopniach
    longitude: float  # Długość geograficzna w stopniach
    elevation: float  # Wysokość n.p.m. w metrach
    name: str = "Unknown"

    def __post_init__(self):
        """Walidacja współrzędnych"""
        if not (-90 <= self.latitude <= 90):
            raise ValueError("Szerokość geograficzna musi być w zakresie -90° do +90°")
        if not (-180 <= self.longitude <= 180):
            raise ValueError("Długość geograficzna musi być w zakresie -180° do +180°")
