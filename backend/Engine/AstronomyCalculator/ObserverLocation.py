from dataclasses import dataclass

from LanguageHelper import LanguageHelper


@dataclass
class ObserverLocation:
    """Observer’s location"""

    languageHelper: LanguageHelper
    latitude: float  # Geographic latitude in degrees
    longitude: float  # Geographic longitude in degrees
    elevation: float  # Elevation above sea level in meters
    name: str = "Unknown"

    def __post_init__(self):
        self._ = self.languageHelper.getTranslatedMessage("AstronomyCalculator")
        """Coordinates validation"""
        if not (-90 <= self.latitude <= 90):
            raise ValueError(f"{self._("observer.location.invalid.latitude.error")} {self.latitude}")
        if not (-180 <= self.longitude <= 180):
            raise ValueError(f"{self._("observer.location.invalid.longitude.error")} {self.longitude}")
