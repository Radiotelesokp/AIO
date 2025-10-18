from dataclasses import dataclass

@dataclass
class Position:
    """Pozycja anteny (azymut i elewacja)"""

    azimuth: float  # stopnie (0-360)
    elevation: float  # stopnie (bez ograniczeń, limity sprawdzane w AntennaController)

    def __post_init__(self):
        """Walidacja pozycji"""
        if not (0 <= self.azimuth <= 360):
            raise ValueError(
                f"Azymut musi być w zakresie 0-360°, otrzymano: {self.azimuth}"
            )
        # Elewacja bez ograniczeń - limity sprawdzane w AntennaController