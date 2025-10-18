from typing import Tuple


class MotorConfig:
    """Konfiguracja silnika z możliwościami kalibracji"""

    def __init__(
        self,
        steps_per_revolution: int = 200,
        microsteps: int = 16,
        azimuth_offset: float = 0.0,
        elevation_offset: float = 0.0,
    ):
        self.steps_per_revolution = steps_per_revolution
        self.microsteps = microsteps

        # Parametry kalibracji
        self.azimuth_offset = azimuth_offset  # Offset kalibracji azymutu w stopniach
        self.elevation_offset = elevation_offset  # Offset kalibracji elewacji w stopniach

    def apply_calibration(
        self, azimuth: float, elevation: float
    ) -> Tuple[float, float]:
        """Stosuje kalibrację do pozycji"""
        calibrated_azimuth = azimuth + self.azimuth_offset
        calibrated_elevation = elevation + self.elevation_offset

        # Normalizuj azymut do zakresu 0-360
        calibrated_azimuth = calibrated_azimuth % 360.0

        return calibrated_azimuth, calibrated_elevation

    def reverse_calibration(
        self, calibrated_azimuth: float, calibrated_elevation: float
    ) -> Tuple[float, float]:
        """Odwraca kalibrację dla uzyskania pozycji raw (tylko offsety)"""
        azimuth = calibrated_azimuth - self.azimuth_offset
        elevation = calibrated_elevation - self.elevation_offset

        # Normalizuj azymut
        azimuth = azimuth % 360.0

        return azimuth, elevation