import json
import logging
import os
from dataclasses import dataclass, asdict
from datetime import time
from typing import Dict, Any

from ..Constants import DEFAULT_CALIBRATION_FILE
from .Position import Position
from ..AntennaControllerHelper import AntennaLimits, AntennaError
from LanguageHelper import LanguageHelper


@dataclass
class PositionCalibration:
    """Antenna position calibration with safety limits"""

    __logger = logging.getLogger(__name__)

    languageHelper: LanguageHelper
    azimuth_offset: float = 0.0  # Offset for azimuth in degrees
    elevation_offset: float = 0.0  # Offset for elevation in degrees

    # Safety limits
    min_azimuth: float = AntennaLimits.min_azimuth  # Minimum azimuth in degrees
    max_azimuth: float = AntennaLimits.max_azimuth  # Maximum azimuth in degrees
    min_elevation: float = AntennaLimits.min_elevation  # Minimum elevation in degrees
    max_elevation: float = AntennaLimits.max_elevation  # Maximum elevation in degrees
    max_azimuth_speed: float = AntennaLimits.max_azimuth_speed  # Maximum azimuth speed in deg/s
    max_elevation_speed: float = AntennaLimits.max_elevation_speed  # Maximum elevation speed in deg/s

    def apply_calibration(self, position: Position) -> Position:
        """Applies calibration to a given position"""

        calibrated_azimuth = (position.azimuth + self.azimuth_offset) % 360
        calibrated_elevation = position.elevation + self.elevation_offset
        calibrated_elevation = max(self.min_elevation, min(self.max_elevation, calibrated_elevation))

        return Position(calibrated_azimuth, calibrated_elevation, self.languageHelper)

    def reverse_calibration(self, calibrated_position: Position) -> Position:
        """Reverses calibration – converts from calibrated position to raw position"""

        raw_azimuth = (calibrated_position.azimuth - self.azimuth_offset) % 360
        raw_elevation = calibrated_position.elevation - self.elevation_offset
        raw_elevation = max(-90.0, min(90.0, raw_elevation))

        return Position(raw_azimuth, raw_elevation, self.languageHelper)

    def get_antenna_limits(self) -> AntennaLimits:
        """Returns antenna limits based on the calibration settings"""
        return AntennaLimits(
            min_azimuth=self.min_azimuth,
            max_azimuth=self.max_azimuth,
            min_elevation=self.min_elevation,
            max_elevation=self.max_elevation,
            max_azimuth_speed=self.max_azimuth_speed,
            max_elevation_speed=self.max_elevation_speed,
        )

    def save_to_file(self, filepath: str = DEFAULT_CALIBRATION_FILE) -> None:
        """Saves calibration and limits to a JSON file"""
        try:
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

            self.__logger.info(f"Calibration with limits saved to file: {filepath}")

        except Exception as e:
            self.__logger.error(f"Error while saving calibration: {e}")
            raise AntennaError(f"Cannot save calibration to file {filepath}: {e}")

    @classmethod
    def load_from_file(self, cls, filepath: str = DEFAULT_CALIBRATION_FILE) -> "PositionCalibration":
        """Loads calibration and limits from a JSON file"""
        try:
            if not os.path.exists(filepath):
                self.__logger.warning(f"Calibration file {filepath} does not exist, using default values")
                return cls()  # Return default calibration

            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Validate data – basic calibration fields
            required_fields = ["azimuth_offset", "elevation_offset"]
            for field in required_fields:
                if field not in data:
                    self.__logger.warning(f"Missing field '{field}' in calibration file, using default value")

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

            self.__logger.info(f"Calibration loaded from file: {filepath}")
            self.__logger.info(
                f"Calibration parameters: "
                f"az_off={calibration.azimuth_offset:.2f}°, "
                f"el_off={calibration.elevation_offset:.2f}°"
            )
            self.__logger.info(
                f"Limits: az({calibration.min_azimuth}°-{calibration.max_azimuth}°), "
                f"el({calibration.min_elevation}°-{calibration.max_elevation}°)"
            )

            return calibration

        except json.JSONDecodeError as e:
            self.__logger.error(f"JSON parsing error in file {filepath}: {e}")
            raise AntennaError(f"Invalid calibration file format: {e}")
        except Exception as e:
            self.__logger.error(f"Error while loading calibration: {e}")
            raise AntennaError(f"Cannot load calibration from file {filepath}: {e}")

    def export_to_dict(self) -> Dict[str, Any]:
        """Exports calibration to a dictionary"""
        return asdict(self)

    @classmethod
    def import_from_dict(self, cls, data: Dict[str, Any]) -> "PositionCalibration":
        """Imports calibration from a dictionary"""
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