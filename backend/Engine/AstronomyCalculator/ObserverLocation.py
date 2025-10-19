from dataclasses import dataclass

@dataclass
class ObserverLocation:
    """Observer’s location"""

    latitude: float  # Geographic latitude in degrees
    longitude: float  # Geographic longitude in degrees
    elevation: float  # Elevation above sea level in meters
    name: str = "Unknown"

    def __init__(self, languageHelper):
        self._ = languageHelper.getTranslatedMessage("AstronomyCalculator")

    def __post_init__(self):
        """Coordinates validation"""
        if not (-90 <= self.latitude <= 90):
            raise ValueError(f"{self._("observer.location.invalid.latitude.error")} {self.latitude}")
        if not (-180 <= self.longitude <= 180):
            raise ValueError(f"{self._("observer.location.invalid.longitude.error")} {self.longitude}")
