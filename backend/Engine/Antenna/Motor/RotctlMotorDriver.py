import logging
import time
from typing import Tuple

from ..Constants import DEFAULT_BAUDRATE
from ..AntennaControllerService import AntennaControllerService
from ..AntennaControllerHelper import CommunicationError, PositionError
from .MotorDriver import MotorDriver
from LanguageHelper import LanguageHelper


class RotctlMotorDriver(MotorDriver):
    """Motor driver communicating via rotctl (Hamlib) using the SPID protocol"""

    __logger = logging.getLogger(__name__)

    def __init__(self, antennaControllerService: AntennaControllerService,
                 languageHelper: LanguageHelper, port: str, baudrate: int = DEFAULT_BAUDRATE):
        self.__antennaControllerService = antennaControllerService
        self.__languageHelper = languageHelper
        self._ = self.__languageHelper.getTranslatedMessage("Antenna")
        self.port = port
        self.baudrate = baudrate
        self.connected = False
        self.current_azimuth = 0.0
        self.current_elevation = 0.0
        self.target_azimuth = 0.0
        self.target_elevation = 0.0
        self.is_moving_flag = False

    def connect(self) -> None:
        """Checks availability of rotctl and port"""
        try:
            if not self.__antennaControllerService.check_rotctl():
                raise CommunicationError(f"{self._('rotctl.motor.hamlib.is.unavailable.error')}")

            # Test connection – try reading the position
            self.current_azimuth, self.current_elevation = self.__antennaControllerService.read_position_rotctl(self.port, self.baudrate)
            self.connected = True
            self.__logger.info(f"Connected to SPID controller via rotctl on port {self.port} (baudrate: {self.baudrate})")
            self.__logger.info(f"Current position: Az={self.current_azimuth:.1f}°, El={self.current_elevation:.1f}°")

        except Exception as e:
            self.__logger.error(f"Error connecting to SPID via rotctl: {e}")
            raise CommunicationError(f"{self._('rotctl.motor.cannot.connect.via.rotctl.error')} {e}")

    def disconnect(self) -> None:
        """Disconnects – rotctl does not require explicit disconnection"""
        self.connected = False
        self.__logger.info("Disconnected from SPID controller (rotctl)")

    def get_position(self) -> Tuple[float, float]:
        """Reads the current antenna position in degrees"""
        if not self.connected:
            raise CommunicationError(f"{self._('rotctl.motor.driver.disconnected.error')}")

        try:
            self.current_azimuth, self.current_elevation = self.__antennaControllerService.read_position_rotctl(
                self.port, self.baudrate)
            return self.current_azimuth, self.current_elevation

        except Exception as e:
            self.__logger.error(f"Error reading position via rotctl: {e}")
            raise CommunicationError(f"Cannot read position via rotctl: {e}")

    def move_to_position(self, azimuth: float, elevation: float) -> None:
        """Moves the antenna to the specified position in degrees"""
        if not self.connected:
            raise CommunicationError(f"{self._('rotctl.motor.driver.disconnected.error')}")

        if not (0 <= azimuth <= 360):  # Range validation
            raise PositionError(f"Azimuth out of range: {azimuth}° (expected 0–360°)")

        try:
            self.target_azimuth = azimuth
            self.target_elevation = elevation
            self.is_moving_flag = True
            self.__logger.info(f"Rotctl: Setting position Az={azimuth:.1f}°, El={elevation:.1f}°")

            time.sleep(0.2)  # Additional delay before sending command
            response = self.__antennaControllerService.set_position_rotctl(self.port, azimuth, elevation, self.baudrate)
            self.__logger.info(f"Rotctl: Command sent. Response: {response}")

        except Exception as e:
            self.is_moving_flag = False
            self.__logger.error(f"Error moving via rotctl: {e}")
            raise CommunicationError(f"{self._('rotctl.motor.cannot.move.antena.error')} {e}")

    def stop(self) -> None:
        """Stops antenna movement"""
        if not self.connected:
            raise CommunicationError(f"{self._('rotctl.motor.driver.disconnected.error')}")

        try:
            self.__logger.info("Rotctl: Stopping antenna movement")
            response = self.__antennaControllerService.stop_rotor_move_rotctl(self.port, self.baudrate)
            self.is_moving_flag = False
            self.__logger.info(f"Rotctl: Movement stopped. Response: {response}")

        except Exception as e:
            self.__logger.error(f"Error stopping via rotctl: {e}")
            raise CommunicationError(f"{self._('rotctl.motor.cannot.stop.antena.error')} {e}")

    def is_moving(self) -> bool:
        """ Checks if the antenna is moving by comparing current and target positions.
        Note: rotctl does not provide a direct movement status, so we check if the position is close to the target."""

        if not self.is_moving_flag:
            return False

        try:
            current_az, current_el = self.get_position()
            az_diff = abs(current_az - self.target_azimuth)  # Position tolerance (1 degree)
            el_diff = abs(current_el - self.target_elevation)

            az_diff = 360 - az_diff if az_diff > 180 else az_diff  # Handle wrap-around 0°/360° for azimuth
            is_at_target = az_diff < 1.0 and el_diff < 1.0

            if is_at_target:
                self.is_moving_flag = False
                self.__logger.info(f"Rotctl: Target position reached Az={current_az:.1f}°, El={current_el:.1f}°")

            return not is_at_target

        except Exception as e:
            self.__logger.warning(f"Error checking movement via rotctl: {e}")
            self.is_moving_flag = False  # Assume movement ended in case of error
            return False