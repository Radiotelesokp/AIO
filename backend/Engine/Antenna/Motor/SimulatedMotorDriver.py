import logging
import time
from typing import Tuple

from backend.Engine.Antenna.AntennaControllerHelper import CommunicationError
from backend.Engine.Antenna.Motor import MotorDriver
from backend.LanguageHelper import LanguageHelper


class SimulatedMotorDriver(MotorDriver):
    """Motor driver simulator for testing – operates directly in degrees"""

    def __init__(self, languageHelper: LanguageHelper, simulation_speed: float = 10.0):
        self.__languageHelper = languageHelper
        self._ = self.__languageHelper.getTranslatedMessage("Antenna")
        self.simulation_speed = simulation_speed  # degrees/s
        self.current_azimuth = 0.0  # degrees
        self.current_elevation = 0.0  # degrees (horizon)
        self.target_azimuth = 0.0
        self.target_elevation = 0.0
        self.connected = False
        self.is_moving_flag = False
        self.last_move_time = time.time()
        self.__logger = logging.getLogger("SimulatedMotorDriver")

    def connect(self) -> None:
        """Simulates establishing a connection"""
        self.connected = True
        self.__logger.info("Connected to motor driver simulator")

    def disconnect(self) -> None:
        """Simulates disconnecting"""
        self.connected = False
        self.__logger.info("Disconnected from motor driver simulator")

    def move_to_position(self, azimuth: float, elevation: float) -> None:
        """Simulates moving to a position in degrees"""
        if not self.connected:
            raise CommunicationError(f"{self._('simulator.motor.is.disconnected')}")

        self.target_azimuth = azimuth
        self.target_elevation = elevation
        self.is_moving_flag = True
        self.last_move_time = time.time()

        self.__logger.info(f"Simulator: Moving to position Az={azimuth}°, El={elevation}°")

    def get_position(self) -> Tuple[float, float]:
        """Returns the current position in degrees, simulating movement"""
        if not self.connected:
            raise CommunicationError(f"{self._('simulator.motor.is.disconnected')}")

        if self.is_moving_flag:
            self._simulate_movement()

        return self.current_azimuth, self.current_elevation

    def _simulate_movement(self) -> None:
        """Simulates smooth antenna movement in degrees"""
        current_time = time.time()
        dt = current_time - self.last_move_time
        self.last_move_time = current_time

        max_move = self.simulation_speed * dt  # Calculate max movement this time step (degrees)
        az_diff = self.target_azimuth - self.current_azimuth  # Azimuth movement
        el_diff = self.target_elevation - self.current_elevation  # Elevation movement

        if abs(az_diff) <= max_move:
            self.current_azimuth = self.target_azimuth
        else:
            self.current_azimuth += max_move if az_diff > 0 else -max_move

        if abs(el_diff) <= max_move:
            self.current_elevation = self.target_elevation
        else:
            self.current_elevation += max_move if el_diff > 0 else -max_move

        # Check if the target is reached
        if abs(self.current_azimuth - self.target_azimuth) < 0.1 and abs(
                self.current_elevation - self.target_elevation) < 0.1:
            self.is_moving_flag = False
            self.__logger.debug("Simulator: Movement completed")

    def stop(self) -> None:
        """Simulates stopping movement"""
        self.is_moving_flag = False

        # Set targets to current position
        self.target_azimuth = self.current_azimuth
        self.target_elevation = self.current_elevation
        self.__logger.info("Simulator: Movement stopped")

    def is_moving(self) -> bool:
        """Checks if the simulator is moving"""
        if self.is_moving_flag:
            self._simulate_movement()
        return self.is_moving_flag