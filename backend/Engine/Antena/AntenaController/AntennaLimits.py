from dataclasses import dataclass


@dataclass
class AntennaLimits:
    """Limity mechaniczne anteny"""

    min_azimuth: float = 0.0
    max_azimuth: float = 360.0
    min_elevation: float = 0.0
    max_elevation: float = 90.0
    max_azimuth_speed: float = 5.0  # stopnie/s
    max_elevation_speed: float = 3.0  # stopnie/s