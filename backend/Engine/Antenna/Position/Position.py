from dataclasses import dataclass
from backend.Engine.Antenna.AntennaControllerHelper import AntennaLimits
from backend.LanguageHelper import LanguageHelper


@dataclass
class Position:
    """Antenna position (azimuth and elevation)"""

    azimuth: float  # degrees (0–360)
    elevation: float  # degrees (no limits, checked in AntennaController)
    languageHelper: LanguageHelper

    def __post_init__(self):
        """Position validation"""
        _ = self.languageHelper.getTranslatedMessage("Antenna")
        if not (AntennaLimits.min_azimuth <= self.azimuth <= AntennaLimits.max_azimuth):
            raise ValueError(f"{_('position.azimuth_limit_error')} {self.azimuth}")
        # Elevation has no limits – limits are checked in AntennaController