from typing import Optional
from dataclasses import dataclass

from backend.Engine.Antenna.Position import Position
from backend.LanguageHelper import LanguageHelper


@dataclass
class AstronomicalPosition:
    """Astronomical position of an object in rotctl convention for SPID"""

    azimuth: float  # Azimuth in degrees (0–360, 0 = north, consistent with rotctl)
    elevation: float  # Elevation in degrees (0–90)
    distance: float  # Distance in AU (astronomical units)
    ra: float  # Right ascension in hours
    dec: float  # Declination in degrees
    is_visible: bool  # Whether the object is above the horizon
    magnitude: float  # Apparent magnitude (if available)
    languageHelper: LanguageHelper

    def to_antenna_position(self) -> Optional[Position]:
        """Converts to antenna position compatible with rotctl for SPID (only if the object is visible)"""
        if not self.is_visible or self.elevation < 0:
            return None
        rotctl_azimuth = self.azimuth

        # Elevation in your system: 0° = vertical (zenith), 90° = horizontal (horizon)
        # PyEphem returns standard elevation (0° = horizon, 90° = zenith)
        # Therefore, we need to invert it: 90° - elevation_pyephem
        rotctl_elevation = 90.0 - self.elevation

        return Position(azimuth=rotctl_azimuth, elevation=rotctl_elevation, languageHelper=self.languageHelper)
