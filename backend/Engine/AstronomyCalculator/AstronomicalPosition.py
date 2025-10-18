from backend.Engine.antenna_controller import Position
from typing import Optional
from dataclasses import dataclass


@dataclass
class AstronomicalPosition:
    """Pozycja astronomiczna obiektu w konwencji rotctl dla SPID"""

    azimuth: float  # Azymut w stopniach (0-360, 0 = północ, zgodnie z rotctl)
    elevation: float  # Elewacja w stopniach (0-90)
    distance: float  # Odległość w AU (jednostki astronomiczne)
    ra: float  # Rektascensja w godzinach
    dec: float  # Deklinacja w stopniach
    is_visible: bool  # Czy obiekt jest nad horyzontem
    magnitude: float  # Jasność pozorna (jeśli dostępna)

    def to_antenna_position(self) -> Optional[Position]:
        """Konwertuje do pozycji anteny zgodnej z rotctl dla SPID (tylko jeśli obiekt jest widoczny)"""
        if not self.is_visible or self.elevation < 0:
            return None
        rotctl_azimuth = self.azimuth

        # Elewacja w waszym systemie: 0° = pion (zenit), 90° = poziom (horyzont)
        # PyEphem zwraca standardową elewację (0° = horyzont, 90° = zenit)
        # Więc musimy odwrócić: 90° - elevation_pyephem
        rotctl_elevation = 90.0 - self.elevation

        return Position(azimuth=rotctl_azimuth, elevation=rotctl_elevation)
