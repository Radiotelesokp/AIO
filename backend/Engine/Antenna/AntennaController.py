import logging
import threading
import time
from typing import Optional, Dict, Any, Callable

from backend.Engine.Antenna import DEFAULT_CALIBRATION_FILE
from backend.Engine.Antenna.AntennaControllerHelper import *
from backend.Engine.Antenna.Motor import MotorDriver, MotorConfig
from backend.Engine.Antenna.Position import Position, PositionCalibration
from backend.LanguageHelper import LanguageHelper


class AntennaController:
    """Main controller for the radio telescope antenna"""
    __logger = logging.getLogger(__name__)

    def __init__(
            self,
            motor_driver: MotorDriver,
            motor_config: MotorConfig,
            languageHelper: LanguageHelper,
            limits: Optional[AntennaLimits] = None,
            update_callback: Optional[Callable] = None,
            position_calibration: Optional[PositionCalibration] = None,
            calibration_file: str = DEFAULT_CALIBRATION_FILE,
    ):
        self.motor_driver = motor_driver
        self.motor_config = motor_config
        self.update_callback = update_callback
        self.calibration_file = calibration_file
        self.__languageHelper = languageHelper
        self._ = self.__languageHelper.getTranslatedMessage("Antenna")

        # Load calibration from file or use the provided one
        if position_calibration is not None:
            self.position_calibration = position_calibration
        else:
            self.position_calibration = PositionCalibration.load_from_file(self.calibration_file)

        # Set limits - use limits from calibration if none were provided
        if limits is not None:
            self.limits = limits
            self.__logger.info("Using provided safety limits")
        else:
            self.limits = self.position_calibration.get_antenna_limits()
            self.__logger.info("Using safety limits from calibration file")

        self.state = AntennaState.IDLE
        self.current_position = Position(0.0, 0.0, self.__languageHelper)
        self.target_position: Optional[Position] = None

        self._monitoring_thread: Optional[threading.Thread] = None
        self._monitoring_active = False
        self._stop_monitoring = threading.Event()

    def initialize(self) -> None:
        """Initializes the antenna system"""
        try:
            self.motor_driver.connect()
            self._start_monitoring()
            self.state = AntennaState.IDLE
            self.__logger.info("Antenna system initialized")
        except Exception as e:
            self.state = AntennaState.ERROR
            raise AntennaError(f"{self._('antenna.initialization.error')} {e}")

    def shutdown(self) -> None:
        """Safely shuts down the antenna system"""
        self.stop()
        self._stop_monitoring.set()
        if self._monitoring_thread and self._monitoring_thread.is_alive():
            self._monitoring_thread.join()
        self.motor_driver.disconnect()
        self.__logger.info("Antenna system shut down")

    def _start_monitoring(self) -> None:
        """Starts the position monitoring thread"""
        self._monitoring_active = True
        self._stop_monitoring.clear()
        self._monitoring_thread = threading.Thread(target=self._monitor_position)
        self._monitoring_thread.daemon = True
        self._monitoring_thread.start()

    def _monitor_position(self) -> None:
        """Monitors antenna position in a separate thread"""
        consecutive_errors = 0
        max_consecutive_errors = 3

        while not self._stop_monitoring.is_set():
            try:
                # All drivers now return values directly in degrees
                azimuth, elevation = self.motor_driver.get_position()
                self.current_position = Position(azimuth, elevation,self.__languageHelper)

                if self.state == AntennaState.MOVING and not self.motor_driver.is_moving():  # Check if movement has finished
                    self.state = AntennaState.IDLE
                    self.__logger.info(f"Movement finished. Position: {self.current_position}")

                if self.update_callback:  # Call update callback if defined
                    self.update_callback(self.current_position, self.state)

                consecutive_errors = 0  # Reset error counter after successful read

            except Exception as e:
                consecutive_errors += 1
                self.__logger.error(f"Monitoring error: {e}")

                # If too many consecutive errors occur, set error state
                if consecutive_errors >= max_consecutive_errors:
                    self.state = AntennaState.ERROR
                    self.__logger.error(f"Too many consecutive monitoring errors ({consecutive_errors})")
                time.sleep(0.2)  # Short pause after an error
            time.sleep(0.5)  # Update every 500ms

    def _validate_position(self, position: Position) -> None:
        """Validates a position against mechanical limits"""
        if not (self.limits.min_azimuth <= position.azimuth <= self.limits.max_azimuth):
            raise SafetyError(f"{self._('antenna.azimuth.out.of.range.error')
                              .format(azimuth=position.azimuth, min_azimuth=self.limits.min_azimuth, max_azimuth=self.limits.max_azimuth)}")
        if not self.limits.min_elevation <= position.elevation <= self.limits.max_elevation:
            raise SafetyError(f"{self._('antenna.elevation.out.of.range.error')
                              .format(el=position.elevation,min_el=self.limits.min_elevation, max_el=self.limits.max_elevation)}")

    def move_to(self, position: Position) -> None:
        """Moves the antenna to the specified position (with calibration applied)"""
        if self.state == AntennaState.ERROR:
            raise AntennaError(f"{self._('antenna.error.state')}")

        calibrated_position = self.position_calibration.apply_calibration(position)  # Apply calibration to target position
        self._validate_position(calibrated_position)  # Validate calibrated position

        try:
            self.target_position = position  # Save the original (uncalibrated) position
            self.state = AntennaState.MOVING
            self.motor_driver.move_to_position(calibrated_position.azimuth, calibrated_position.elevation)  # All drivers now take degrees
            self.__logger.info(f"Started movement to position: {position} (calibrated: {calibrated_position})")

        except Exception as e:
            self.state = AntennaState.ERROR
            raise PositionError(f"{self._('antenna.movement.error')} {e}")

    def get_current_position(self, apply_reverse_calibration: bool = True) -> Position:
        """Returns the current antenna position"""
        if apply_reverse_calibration:
            return self.position_calibration.reverse_calibration(self.current_position)  # Return position with reversed calibration (logical position)
        else:
            return self.current_position  # Return raw sensor position

    def set_position_calibration(self, calibration: PositionCalibration, save_to_file: bool = True, update_limits: bool = True) -> None:
        """Sets position calibration"""
        self.position_calibration = calibration

        # Update limits based on calibration if required
        if update_limits:
            self.limits = calibration.get_antenna_limits()
            self.__logger.info("Safety limits updated based on calibration")

        if save_to_file:
            try:
                calibration.save_to_file(self.calibration_file)
                self.__logger.info("Calibration automatically saved to file")
            except Exception as e:
                self.__logger.warning(f"Failed to save calibration to file: {e}")

        self.__logger.info(
            f"Position calibration set: offset_az={calibration.azimuth_offset}°, "
            f"offset_el={calibration.elevation_offset}°"
        )
        self.__logger.info(
            f"Limits: az({calibration.min_azimuth}°–{calibration.max_azimuth}°), "
            f"el({calibration.min_elevation}°–{calibration.max_elevation}°)"
        )

    def save_calibration(self, filepath: Optional[str] = None) -> None:
        """Saves the current calibration to a file"""
        file_to_use = filepath or self.calibration_file
        self.position_calibration.save_to_file(file_to_use)
        self.__logger.info(f"Calibration saved to {file_to_use}")

    def load_calibration(self, filepath: Optional[str] = None, update_limits: bool = True) -> None:
        """Loads calibration from a file"""
        file_to_use = filepath or self.calibration_file
        self.position_calibration = PositionCalibration.load_from_file(file_to_use)

        # Update limits based on loaded calibration
        if update_limits:
            self.limits = self.position_calibration.get_antenna_limits()
            self.__logger.info("Safety limits updated based on loaded calibration")

        self.__logger.info(f"Calibration loaded from {file_to_use}")

    def reset_calibration(self, save_to_file: bool = True, update_limits: bool = True) -> None:
        """Resets calibration to default values"""
        self.position_calibration = PositionCalibration(self.__languageHelper)

        # Update limits based on default calibration
        if update_limits:
            self.limits = self.position_calibration.get_antenna_limits()
            self.__logger.info("Safety limits reset to default values")

        if save_to_file:
            try:
                self.save_calibration()
                self.__logger.info("Reset calibration saved to file")
            except Exception as e:
                self.__logger.warning(f"Failed to save reset calibration: {e}")

        self.__logger.info("Calibration reset to default values")

    def calibrate_azimuth_reference(self, current_azimuth: float = None, save_to_file: bool = True) -> None:
        """Calibrates the azimuth reference"""
        if current_azimuth is None:
            current_azimuth = self.current_position.azimuth

        offset = -current_azimuth  # Calculate offset so that current azimuth becomes 0°
        self.position_calibration.azimuth_offset = offset

        if save_to_file:
            try:
                self.save_calibration()
                self.__logger.info("Azimuth calibration saved to file")
            except Exception as e:
                self.__logger.warning(f"Failed to save azimuth calibration: {e}")

        self.__logger.info(f"Azimuth calibrated: offset={offset}°")

    def stop(self) -> None:
        """Stops antenna movement"""
        try:
            self.motor_driver.stop()
            self.state = AntennaState.STOPPED
            self.target_position = None
            self.__logger.info("Antenna movement stopped")
        except Exception as e:
            self.state = AntennaState.ERROR
            raise AntennaError(f"{self._('antenna.stop.error')} {e}")

    def calibrate(self) -> None:
        """Calibrates antenna position (returns to home position)"""
        self.__logger.info("Starting calibration...")
        self.state = AntennaState.CALIBRATING

        home_position = Position(0.0, 0.0, self.__languageHelper)  # Return to position 0,0
        self.move_to(home_position)

        while self.state == AntennaState.MOVING:  # Wait until calibration is done
            time.sleep(0.1)

        self.state = AntennaState.IDLE
        self.__logger.info("Calibration completed")

    def get_status(self) -> Dict[str, Any]:
        """Returns full antenna status"""
        return {
            "state": self.state.value,
            "current_position": {
                "azimuth": self.current_position.azimuth,
                "elevation": self.current_position.elevation,
            },
            "target_position": (
                {
                    "azimuth": self.target_position.azimuth,
                    "elevation": self.target_position.elevation,
                }
                if self.target_position
                else None
            ),
            "is_moving": (
                self.motor_driver.is_moving()
                if hasattr(self.motor_driver, "is_moving")
                else False
            ),
            "limits": {
                "azimuth": (self.limits.min_azimuth, self.limits.max_azimuth),
                "elevation": (self.limits.min_elevation, self.limits.max_elevation),
                "max_speeds": {
                    "azimuth": self.limits.max_azimuth_speed,
                    "elevation": self.limits.max_elevation_speed,
                },
            },
            "calibration": {
                "azimuth_offset": self.position_calibration.azimuth_offset,
                "elevation_offset": self.position_calibration.elevation_offset,
                "limits": {
                    "min_azimuth": self.position_calibration.min_azimuth,
                    "max_azimuth": self.position_calibration.max_azimuth,
                    "min_elevation": self.position_calibration.min_elevation,
                    "max_elevation": self.position_calibration.max_elevation,
                    "max_azimuth_speed": self.position_calibration.max_azimuth_speed,
                    "max_elevation_speed": self.position_calibration.max_elevation_speed,
                },
            },
            "calibration_file": self.calibration_file,
        }

    def reset_error(self) -> None:
        """Resets controller error state"""
        if self.state == AntennaState.ERROR:
            self.state = AntennaState.IDLE
            self.__logger.info("Error state has been reset")

    def wait_for_movement(self, timeout: float = 90.0) -> None:
        """
        Waits for movement to finish with a timeout.
        Checks both controller state and actual antenna motion.

        Args:
            timeout: Maximum wait time in seconds

        Raises:
            TimeoutError: When waiting time is exceeded
        """

        start_time = time.time()
        last_movement_time = start_time
        prev_position = None

        while True:
            current_time = time.time()
            elapsed_time = current_time - start_time

            try:
                current_position = self.current_position  # Get current position

                # Check if antenna is moving (compare with previous position)
                if prev_position is not None:
                    az_moved = abs(current_position.azimuth - prev_position.azimuth)
                    az_moved = 360 - az_moved if az_moved > 180 else az_moved  # Account for azimuth wrap-around
                    el_moved = abs(current_position.elevation - prev_position.elevation)

                    # If antenna has moved (>0.2°), update last movement time
                    if az_moved > 0.2 or el_moved > 0.2:
                        last_movement_time = current_time
                        self.__logger.debug(f"Antenna movement detected: dAz={az_moved:.1f}°, dEl={el_moved:.1f}°")

                # Check controller state - if not moving and stable for some time
                time_since_movement = current_time - last_movement_time
                if self.state != AntennaState.MOVING and time_since_movement > 3.0:  # 3s of no movement = stable
                    self.__logger.debug(f"Movement finished - state: {self.state}, no movement for {time_since_movement:.1f}s")
                    break

                # Check timeout - only if no movement for last 10 seconds
                if elapsed_time > timeout and time_since_movement > 10.0:
                    self.stop()
                    raise TimeoutError(f"{self._('antenna.timeout.movement.error').format(timeout=timeout, time_site = round(time_since_movement, 1))}")

                prev_position = current_position # Save position for next iteration
                time.sleep(0.5)

            except Exception as e:
                if isinstance(e, TimeoutError):
                    raise
                self.__logger.warning(f"Error while checking movement: {e}")
                time.sleep(0.5)
