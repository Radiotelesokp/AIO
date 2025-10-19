import logging
import time
import json
import os
from dataclasses import dataclass, asdict
from typing import Dict, Any

from backend.Engine.Antenna import DEFAULT_CALIBRATION_FILE
from backend.Engine.Antenna.AntennaControllerHelper import AntennaLimits, AntennaError
from backend.Engine.Antenna.Position import Position


@dataclass
class PositionCalibration:
    """Kalibracja pozycji anteny z limitami bezpieczeństwa"""
    
    __logger = logging.getLogger(__name__)

    azimuth_offset: float = 0.0  # Offset dla azymutu w stopniach
    elevation_offset: float = 0.0  # Offset dla elewacji w stopniach

    # Limity bezpieczeństwa
    min_azimuth: float = 0.0  # Minimalny azimut w stopniach
    max_azimuth: float = 360.0  # Maksymalny azimut w stopniach
    min_elevation: float = 0.0  # Minimalna elewacja w stopniach
    max_elevation: float = 90.0  # Maksymalna elewacja w stopniach
    max_azimuth_speed: float = 5.0  # Maksymalna prędkość azymutu w stopniach/s
    max_elevation_speed: float = 3.0  # Maksymalna prędkość elewacji w stopniach/s

    def apply_calibration(self, position: Position) -> Position:
        """Aplikuje kalibrację do pozycji"""
        # Aplikuj offset azymutu
        calibrated_azimuth = (position.azimuth + self.azimuth_offset) % 360

        # Aplikuj offset elewacji
        calibrated_elevation = position.elevation + self.elevation_offset

        # Ogranicz elewację do zakresów z kalibracji
        calibrated_elevation = max(self.min_elevation, min(self.max_elevation, calibrated_elevation))

        return Position(calibrated_azimuth, calibrated_elevation)

    def reverse_calibration(self, calibrated_position: Position) -> Position:
        """Odwraca kalibrację - konwertuje z pozycji skalibrowanej do surowej"""
        # Cofnij offset azymutu
        raw_azimuth = (calibrated_position.azimuth - self.azimuth_offset) % 360

        # Cofnij offset elewacji
        raw_elevation = calibrated_position.elevation - self.elevation_offset

        # Ogranicz do sensownych zakresów
        raw_elevation = max(-90.0, min(90.0, raw_elevation))

        return Position(raw_azimuth, raw_elevation)

    def get_antenna_limits(self) -> AntennaLimits:
        """Zwraca limity anteny na podstawie ustawień kalibracji"""
        return AntennaLimits(
            min_azimuth=self.min_azimuth,
            max_azimuth=self.max_azimuth,
            min_elevation=self.min_elevation,
            max_elevation=self.max_elevation,
            max_azimuth_speed=self.max_azimuth_speed,
            max_elevation_speed=self.max_elevation_speed,
        )

    def save_to_file(self, filepath: str = DEFAULT_CALIBRATION_FILE) -> None:
        """Zapisuje kalibrację i limity do pliku JSON"""
        try:
            # Utwórz folder jeśli nie istnieje
            os.makedirs(os.path.dirname(filepath), exist_ok=True)

            calibration_data = {
                "azimuth_offset": self.azimuth_offset,
                "elevation_offset": self.elevation_offset,
                "min_azimuth": self.min_azimuth,
                "max_azimuth": self.max_azimuth,
                "min_elevation": self.min_elevation,
                "max_elevation": self.max_elevation,
                "max_azimuth_speed": self.max_azimuth_speed,
                "max_elevation_speed": self.max_elevation_speed,
                "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "version": "2.0",
            }

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(calibration_data, f, indent=4, ensure_ascii=False)

            self.__logger.info(f"Kalibracja z limitami zapisana do pliku: {filepath}")

        except Exception as e:
            self.__logger.error(f"Błąd podczas zapisywania kalibracji: {e}")
            raise AntennaError(f"Nie można zapisać kalibracji do pliku {filepath}: {e}")

    @classmethod
    def load_from_file(self, cls, filepath: str = DEFAULT_CALIBRATION_FILE) -> "PositionCalibration":
        """Wczytuje kalibrację i limity z pliku JSON"""
        try:
            if not os.path.exists(filepath):
                self.__logger.warning(
                    f"Plik kalibracji {filepath} nie istnieje, używam domyślnych wartości"
                )
                return cls()  # Zwróć domyślną kalibrację

            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Walidacja danych - podstawowe pola kalibracji
            required_fields = [
                "azimuth_offset",
                "elevation_offset",
            ]
            for field in required_fields:
                if field not in data:
                    self.__logger.warning(
                        f"Brak pola '{field}' w pliku kalibracji, używam wartości domyślnej"
                    )

            calibration = cls(
                azimuth_offset=float(data.get("azimuth_offset", 0.0)),
                elevation_offset=float(data.get("elevation_offset", 0.0)),
                min_azimuth=float(data.get("min_azimuth", 0.0)),
                max_azimuth=float(data.get("max_azimuth", 360.0)),
                min_elevation=float(data.get("min_elevation", 0.0)),
                max_elevation=float(data.get("max_elevation", 90.0)),
                max_azimuth_speed=float(data.get("max_azimuth_speed", 5.0)),
                max_elevation_speed=float(data.get("max_elevation_speed", 3.0)),
            )

            self.__logger.info(f"Kalibracja wczytana z pliku: {filepath}")
            self.__logger.info(
                f"Parametry kalibracji: "
                f"az_off={calibration.azimuth_offset:.2f}°, "
                f"el_off={calibration.elevation_offset:.2f}°"
            )
            self.__logger.info(
                f"Limity: az({calibration.min_azimuth}°-{calibration.max_azimuth}°), "
                f"el({calibration.min_elevation}°-{calibration.max_elevation}°)"
            )

            return calibration

        except json.JSONDecodeError as e:
            self.__logger.error(f"Błąd parsowania JSON w pliku {filepath}: {e}")
            raise AntennaError(f"Nieprawidłowy format pliku kalibracji: {e}")
        except Exception as e:
            self.__logger.error(f"Błąd podczas wczytywania kalibracji: {e}")
            raise AntennaError(f"Nie można wczytać kalibracji z pliku {filepath}: {e}")

    def export_to_dict(self) -> Dict[str, Any]:
        """Eksportuje kalibrację do słownika"""
        return asdict(self)

    @classmethod
    def import_from_dict(self, cls, data: Dict[str, Any]) -> "PositionCalibration":
        """Importuje kalibrację ze słownika"""
        return cls(
            azimuth_offset=float(data.get("azimuth_offset", 0.0)),
            elevation_offset=float(data.get("elevation_offset", 0.0)),
            min_azimuth=float(data.get("min_azimuth", 0.0)),
            max_azimuth=float(data.get("max_azimuth", 360.0)),
            min_elevation=float(data.get("min_elevation", 0.0)),
            max_elevation=float(data.get("max_elevation", 90.0)),
            max_azimuth_speed=float(data.get("max_azimuth_speed", 5.0)),
            max_elevation_speed=float(data.get("max_elevation_speed", 3.0)),
        )