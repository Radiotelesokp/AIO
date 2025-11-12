from typing import Tuple


class MotorConfig:
    """Motor configuration with calibration capabilities"""

    def __init__(self, steps_per_revolution: int = 200, microsteps: int = 16, azimuth_offset: float = 0.0,
                 elevation_offset: float = 0.0):
        self.steps_per_revolution = steps_per_revolution
        self.microsteps = microsteps

        # Calibration parameters
        self.azimuth_offset = azimuth_offset  # Azimuth calibration offset in degrees
        self.elevation_offset = elevation_offset  # Elevation calibration offset in degrees

    def apply_calibration(self, azimuth: float, elevation: float) -> Tuple[float, float]:
        """Applies calibration to a position"""
        calibrated_azimuth = azimuth + self.azimuth_offset
        calibrated_elevation = elevation + self.elevation_offset
        calibrated_azimuth = calibrated_azimuth % 360.0  # Normalize azimuth to 0–360 range

        return calibrated_azimuth, calibrated_elevation

    def reverse_calibration(self, calibrated_azimuth: float, calibrated_elevation: float) -> Tuple[float, float]:
        """Reverses calibration to obtain the raw position (offsets only)"""
        azimuth = calibrated_azimuth - self.azimuth_offset
        elevation = calibrated_elevation - self.elevation_offset
        azimuth = azimuth % 360.0  # Normalize azimuth

        return azimuth, elevation
