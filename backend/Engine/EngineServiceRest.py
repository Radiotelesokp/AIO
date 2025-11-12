import asyncio
import logging
from typing import Optional

from fastapi.responses import JSONResponse

from .Antenna import AntennaControllerFactory, DEFAULT_SPID_PORT, DEFAULT_BAUDRATE, AntennaController, \
    AntennaControllerService
from .Antenna.AntennaControllerHelper import AntennaState
from .Antenna.Model import PositionModel, ObserverLocationModel, StatusResponse, ConnectionConfigModel, \
    AxisMoveModel, CalibrationModel, AzimuthCalibrationModel, TrackingConfigModel
from .Antenna.Motor.MotorConfig import MotorConfig
from .Antenna.Position import Position, PositionCalibration


from .AstronomyCalculator import AstronomicalCalculator, ObserverLocation, \
    AstronomicalObjectType, AstronomicalTracker
from LanguageHelper import LanguageHelper

class EngineServiceRest:
    __logger = logging.getLogger(__name__)

    __antenna_controller: Optional[AntennaController] = None
    __antennaControllerService: AntennaControllerService = None
    __astro_calculator: Optional[AstronomicalCalculator] = None
    __current_observer_location: Optional[ObserverLocation] = None
    __astro_tracker: Optional[AstronomicalTracker] = None
    __tracking_active: bool = False
    __tracking_task: Optional[asyncio.Task] = None
    __current_port: Optional[str] = None

    def __init__(self, languageHelper: LanguageHelper):
        self.__languageHelper = languageHelper
        self._ = self.__languageHelper.getTranslatedMessage("Antenna")


    def emergency_stop(self, port=DEFAULT_SPID_PORT, speed: int = DEFAULT_BAUDRATE) -> bool:
        """Perform an emergency stop of the antenna."""
        success = False
        self.__logger.warning(f'Emergency stop triggered. Used port for Hamlib: {port}.')

        if not self.__antennaControllerService.check_rotctl():
            self.__logger.error("rotctl (Hamlib) is not available on the system.")
        else:
            result = self.__antennaControllerService.stop_rotor_move_rotctl(port, speed)

            if "OK" in result or "STOP" in result:
                self.__logger.info(f"Successfully stopped: {result.strip()}.")
                success = True
            else:
                self.__logger.error(f"Error during emergency stop: {result.strip()}.")

        return success


    def get_status(self):
        """Retrieve the current status of the antenna system."""
        connected = (self.__antenna_controller is not None and
                     hasattr(self.__antenna_controller.motor_driver, 'connected') and
                     self.__antenna_controller.motor_driver.connected)
        current_position = None
        is_moving = False
        last_error = None

        if connected:
            try:
                # Use get_current_position() with calibration instead of raw current_position
                pos = self.__antenna_controller.get_current_position(apply_reverse_calibration=True)
                if pos:
                    current_position = PositionModel(azimuth=pos.azimuth, elevation=pos.elevation)
                is_moving = self.__antenna_controller.state == AntennaState.MOVING
            except Exception as e:
                last_error = str(e)
                self.__logger.error(f"Error retrieving status: {e}.")

        observer_loc = None
        if self.__current_observer_location:
            observer_loc = ObserverLocationModel(
                latitude=self.__current_observer_location.latitude,
                longitude=self.__current_observer_location.longitude,
                elevation=self.__current_observer_location.elevation,
                name=self.__current_observer_location.name
            )

        return StatusResponse(connected=connected, current_position=current_position, is_moving=is_moving,
            last_error=last_error, observer_location=observer_loc, port=self.__current_port)


    def connect_antenna(self, config: ConnectionConfigModel):
        """Connect to the antenna."""
        try:
            if config.use_simulator:
                self.__logger.info("Connecting to simulator...")
                self.__antenna_controller = AntennaControllerFactory.create_simulator_controller(
                    simulation_speed=2000.0, motor_config=MotorConfig())
                self.__current_port = "Simulator"
            else:
                port = config.port
                if not port:
                    # Use the default or the best available port
                    self.__logger.info("Searching for the best SPID port...")
                    port = self.__antennaControllerService.get_best_spid_port()
                    self.__logger.info(f"Selected port: {port}.")

                self.__logger.info(f"Connecting to port {port}...")
                self.__antenna_controller = AntennaControllerFactory.create_spid_controller(
                    port=port, baudrate=config.baudrate, motor_config=MotorConfig())
                self.__current_port = port

            self.__antenna_controller.initialize()  # Initialize the controller
            self.__logger.info("Connection successfully established.")

            return JSONResponse(status_code=200,
                                content={"status": "Connected", "port": self.__current_port, "simulator": config.use_simulator})

        except Exception as e:
            self.__logger.error(f"Connection error: {e}")
            return JSONResponse(status_code=500,
                                content={"message": f"{self._('rest.antenna.connection.error')} {str(e)}"})


    def disconnect_antenna(self):
        """Disconnect from the antenna."""
        try:
            if self.__antenna_controller:
                self.__antenna_controller.stop()
                self.__antenna_controller.shutdown()
                self.__antenna_controller = None
                self.__current_port = None

            self.__logger.info("Antenna disconnected.")
            return {"status": "disconnected"}

        except Exception as e:
            self.__logger.error(f"Disconnection error: {e}")
            return JSONResponse(status_code=500,
                                content={"message": f"{self._('rest.antenna.connection.error')} {str(e)}"})


    def get_position(self):
        """Retrieve the current calibrated antenna position."""
        controller = self.__get_antenna_controller()

        try:
            pos = controller.get_current_position(apply_reverse_calibration=True)
            if pos is None:
                return JSONResponse(status_code=404,
                                    content={"message": f"{self._('rest.antenna.unable.retrieve.position')}"})

            return PositionModel(azimuth=pos.azimuth, elevation=pos.elevation)

        except Exception as e:
            self.__logger.error(f"Error retrieving position: {e}")
            return JSONResponse(status_code=500,
                                content={"message": f"{self._('rest.antenna.retrieving.position.error')} {str(e)}"})


    def set_position(self, position: PositionModel):
        """Set a new antenna position."""
        controller = self.__get_antenna_controller()

        try:
            target_pos = Position(position.azimuth, position.elevation, self.__languageHelper)
            controller.move_to(target_pos)
            return JSONResponse(status_code=200, content={"status": "moving", "target": position.model_dump()})

        except Exception as e:
            self.__logger.error(f"Error setting position: {e}")
            return JSONResponse(status_code=500,
                                content={"message": f"{self._('rest.antenna.setting.position.error')} {str(e)}"})


    def stop_antenna(self):
        """Immediately stop the antenna."""
        controller = self.__get_antenna_controller()

        try:
            controller.stop()
            self.__logger.info("Antenna stopped")
            return JSONResponse(status_code=200, content={"status": "stopped"})

        except Exception as e:
            self.__logger.error(f"Error stopping antenna: {e}")
            return JSONResponse(status_code=500,
                                content={"message": f"{self._('rest.antenna.stopping.antenna.error')} {str(e)}"})


    def set_observer_location(self, location: ObserverLocationModel):
        """Set observer location for astronomical calculations."""
        try:
            self.__current_observer_location = ObserverLocation(latitude=location.latitude,
                                                                longitude=location.longitude,
                                                                elevation=location.elevation,
                                                                name=location.name,
                                                                languageHelper=self.__languageHelper)

            self.__astro_calculator = AstronomicalCalculator(self.__current_observer_location, self.__languageHelper)
            self.__astro_tracker = AstronomicalTracker(self.__astro_calculator)
            self.__logger.info(f"Observer location set: {location.name}")

            return JSONResponse(status_code=200, content={"status": "set", "location": location.model_dump()})

        except Exception as e:
            self.__logger.error(f"Error setting observer location: {e}")
            return JSONResponse(status_code=500,
                                content={"message": f"{self._('rest.antenna.setting.location.error')} {str(e)}"})


    def get_observer_location(self):
        """Retrieve the current observer location."""
        if self.__current_observer_location is None:
            return JSONResponse(status_code=410,
                                content={"message": f"{self._('rest.antenna.location.not.set')}"})

        return JSONResponse(status_code=200, content=ObserverLocationModel(
            latitude=self.__current_observer_location.latitude,
            longitude=self.__current_observer_location.longitude,
            elevation=self.__current_observer_location.elevation,
            name=self.__current_observer_location.name))

    def track_object(self, object_name: str, object_type: AstronomicalObjectType = AstronomicalObjectType.SUN):
        """Start tracking an astronomical object."""
        controller = self.__get_antenna_controller()
        calculator = self.__get_astro_calculator()

        try:
            # Calculate the object's position
            if object_type == AstronomicalObjectType.SUN:
                position = calculator.get_sun_position()
            elif object_type == AstronomicalObjectType.MOON:
                position = calculator.get_moon_position()
            elif object_name.lower() in ["mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune"]:
                planet_type = AstronomicalObjectType(object_name.lower())
                position = calculator.get_planet_position(planet_type)
            else:
                position = calculator.get_star_position(object_name)

            if position is None or not position.is_visible:
                return JSONResponse(status_code=404, content={"message": f"{self._('rest.antenna.object.is.not.visible').format(name=object_name)}"})

            # Convert to antenna position and move
            antenna_position = position.to_antenna_position()
            if antenna_position:
                controller.move_to(antenna_position)
            else:
                return JSONResponse(status_code=400,
                                    content={"message": f"{self._('rest.antenna.object.out.of.range.error').format(name=object_name)}"})

            self.__logger.info(f"Antenna moved to object: {object_name}")
            return JSONResponse(status_code=200, content={
                "status": "moved_to_object",
                "object": object_name,
                "type": object_type.value,
                "position": {"azimuth": position.azimuth, "elevation": position.elevation}
            })

        except Exception as e:
            self.__logger.error(f"Error moving to object: {e}")
            return JSONResponse(status_code=500,
                                content={"message": f"{self._('rest.antenna.error.moving.to.object')} {str(e)}"})

    def start_tracking(self, config: TrackingConfigModel):
        """Start continuous tracking of an astronomical object."""
        if self.__tracking_active:
            return JSONResponse(status_code=400,
                                    content={"message": f"{self._('rest.antenna.tracking.is.active')}"})

        try:
            # Ensure required components are available
            self.__get_antenna_controller()
            self.__get_astro_tracker()

            self.__tracking_active = True
            self.__tracking_task = asyncio.create_task(self.__continuous_tracking_task(config))

            self.__logger.info(f"Started continuous tracking of object: {config.object_name}")
            return JSONResponse(status_code=200, content={
                "status": "tracking_started",
                "object": config.object_name,
                "type": config.object_type.value,
                "config": config.model_dump()
            })

        except Exception as e:
            self.__tracking_active = False
            self.__logger.error(f"Error starting tracking: {e}")
            return JSONResponse(status_code=500,
                                content={"message": f"{self._('rest.antenna.starting.tracking.error')} {str(e)}"})

    async def stop_tracking(self):
        """Stop tracking the astronomical object."""
        try:
            if self.__tracking_active:
                self.__tracking_active = False
                if self.__tracking_task and not self.__tracking_task.done():
                    self.__tracking_task.cancel()
                    try:
                        await self.__tracking_task
                    except asyncio.CancelledError:
                        pass
                self.__tracking_task = None

            # Also stop the antenna
            controller = self.__get_antenna_controller()
            controller.stop()

            self.__logger.info("Tracking stopped")
            return JSONResponse(status_code=200, content={"status": "tracking_stopped"})

        except Exception as e:
            self.__logger.error(f"Error stopping tracking: {e}")
            return JSONResponse(status_code=500, content={"message": f"{self._('rest.antenna.stopping.tracking.error')} {str(e)}"})

    def get_tracking_status(self):
        """Get current tracking status."""
        return JSONResponse(status_code =200, content={"tracking_active": self.__tracking_active,
            "task_running": self.__tracking_task is not None and not self.__tracking_task.done() if self.__tracking_task else False})

    def list_ports(self):
        """List available serial ports."""
        try:
            # Return the default SPID port
            return JSONResponse(status_code=200, content={"ports": [DEFAULT_SPID_PORT], "default_port": DEFAULT_SPID_PORT})

        except Exception as e:
            self.__logger.error(f"Error listing ports: {e}")
            return JSONResponse(status_code=500, content=f"{self._('rest.antenna.listing.ports.error')} {str(e)}")

    def diagnostic(self):
        """Check if rotctl and SPID are operational."""
        try:
            rotctl_available = self.__antennaControllerService.check_rotctl()
            spid_connected = self.__antennaControllerService.test_spid_connection(DEFAULT_SPID_PORT, DEFAULT_BAUDRATE)

            return JSONResponse(status_code=200, content={
                "rotctl_available": rotctl_available,
                "rotctl_version": "Available" if rotctl_available else "N/A",
                "spid_connected": spid_connected,
                "spid_error": "SPID not responding" if not spid_connected else "OK",
                "default_port": DEFAULT_SPID_PORT,
                "recommendation": ("Use simulator if SPID is unresponsive" if not spid_connected else "SPID ready")})

        except Exception as e:
            self.__logger.error(f"Diagnostic error: {e}")
            return JSONResponse(status_code=500, content=f"{self._('rest.antenna.diagnostic.error')} {str(e)}")


    def get_astronomical_position(self, object_name: str):
        """Get the current position of an astronomical object."""
        calculator = self.__get_astro_calculator()

        try:
            object_name_lower = object_name.lower()

            # Map objects to correct types
            if object_name_lower == "sun":
                position = calculator.get_sun_position()
            elif object_name_lower == "moon":
                position = calculator.get_moon_position()
            elif object_name_lower in ["mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune"]:
                planet_type = AstronomicalObjectType(object_name_lower)
                position = calculator.get_planet_position(planet_type)
            else:
                position = calculator.get_star_position(object_name)

            if position is None:
                return JSONResponse(status_code=404,
                                    content=f"{self._('rest.antenna.unable.position.computing.error')} {object_name}")

            if not position.is_visible:
                self.__logger.warning(f"Object {object_name} is below the horizon")

            # Convert to antenna position (with proper elevation conversion)
            antenna_position = position.to_antenna_position()
            if antenna_position is None:
                # Object not visible, return raw data
                converted_elevation = 90.0 - position.elevation if position.elevation >= 0 else position.elevation
            else:
                converted_elevation = antenna_position.elevation

            return JSONResponse(status_code=200, content={
                "azimuth": position.azimuth,
                "elevation": converted_elevation,
                "distance": position.distance,
                "ra": position.ra,
                "dec": position.dec,
                "is_visible": position.is_visible,
                "magnitude": position.magnitude if hasattr(position, 'magnitude') else None
            })

        except ValueError:
            self.__logger.error(f"Invalid astronomical object: {object_name}")
            return JSONResponse(status_code=400, content=f"{self._('rest.antenna.invalid.astronomical.object')} {object_name}")
        except Exception as e:
            self.__logger.error(f"Error computing position for object {object_name}: {e}")
            return JSONResponse(status_code=500, content=f"{self._('rest.antenna.position.computing.error')} {str(e)}")


    def calibrate_azimuth_reference(self, calibration: AzimuthCalibrationModel):
        """Calibrate the azimuth reference point (set a new 0°)."""
        controller = self.__get_antenna_controller()

        try:
            controller.calibrate_azimuth_reference(current_azimuth=calibration.current_azimuth,
                                                   save_to_file=calibration.save_to_file)

            self.__logger.info(f"Azimuth calibration completed. Offset: {controller.position_calibration.azimuth_offset:.2f}°")
            return JSONResponse(status_code=200, content={
                "status": "calibrated",
                "azimuth_offset": controller.position_calibration.azimuth_offset,
                "saved_to_file": calibration.save_to_file
            })

        except Exception as e:
            self.__logger.error(f"Azimuth calibration error: {e}")
            return JSONResponse(status_code=500, content=f"{self._('rest.antenna.azimuth.calibration.error')} {str(e)}")

    def get_calibration(self):
        """Get current calibration parameters."""
        controller = self.__get_antenna_controller()

        try:
            cal = controller.position_calibration
            return JSONResponse(status_code=200, content=CalibrationModel(
                azimuth_offset=cal.azimuth_offset, elevation_offset=cal.elevation_offset))

        except Exception as e:
            self.__logger.error(f"Error fetching calibration: {e}")
            return JSONResponse(status_code=500, content=f"{self._('rest.antenna.fetching.calibration.error')} {str(e)}")

    def set_calibration(self, calibration: CalibrationModel):
        """Set calibration parameters."""
        controller = self.__get_antenna_controller()

        try:
            new_cal = PositionCalibration(
                azimuth_offset=calibration.azimuth_offset,
                elevation_offset=calibration.elevation_offset,
                languageHelper=self.__languageHelper
            )
            controller.set_position_calibration(new_cal, save_to_file=True)
            self.__logger.info("Calibration set and saved")
            return JSONResponse(status_code=200, content={"status": "set", "calibration": calibration.model_dump()})

        except Exception as e:
            self.__logger.error(f"Error setting calibration: {e}")
            return JSONResponse(status_code=500, content=f"{self._('rest.antenna.setting.calibration.error')} {str(e)}")

    def reset_calibration(self):
        """Reset calibration to default values."""
        controller = self.__get_antenna_controller()

        try:
            controller.reset_calibration(save_to_file=True)
            self.__logger.info("Calibration reset to default values")
            return JSONResponse(status_code=200, content={"status": "reset", "message": "Calibration reset to default values"})

        except Exception as e:
            self.__logger.error(f"Error resetting calibration: {e}")
            return JSONResponse(status_code=500, content=f"{self._('rest.antenna.resetting.calibration.error')} {str(e)}")

    def move_axis(self, move: AxisMoveModel):
        """Move the antenna along a specified axis by a given amount."""
        controller = self.__get_antenna_controller()

        try:
            # Use calibrated position for calculations
            current_pos = controller.get_current_position(apply_reverse_calibration=True)

            if move.axis.lower() == "azimuth":
                if move.direction.lower() == "positive":
                    new_azimuth = (current_pos.azimuth + move.amount) % 360
                else:  # negative
                    new_azimuth = (current_pos.azimuth - move.amount) % 360
                new_position = Position(azimuth=new_azimuth,
                        elevation=current_pos.elevation, languageHelper=self.__languageHelper)

            elif move.axis.lower() == "elevation":
                if move.direction.lower() == "positive":
                    new_elevation = current_pos.elevation + move.amount
                else:  # negative
                    new_elevation = current_pos.elevation - move.amount
                new_position = Position(azimuth=current_pos.azimuth,
                    elevation=new_elevation, languageHelper=self.__languageHelper)

            else:
                return JSONResponse(status_code=500, content=f"{self._('rest.antenna.wrong.axis')}")

            controller.move_to(new_position)
            self.__logger.info(f"Axis move {move.axis}: {move.direction} by {move.amount}°")
            return JSONResponse(status_code=200, content={
                "status": "moving",
                "axis": move.axis,
                "direction": move.direction,
                "amount": move.amount,
                "new_position": {"azimuth": new_position.azimuth, "elevation": new_position.elevation}})

        except Exception as e:
            self.__logger.error(f"Axis move error: {e}")
            return JSONResponse(status_code=500, content=f"{self._('rest.antenna.axis.move.error')} {str(e)}")

    # Helper functions
    def __get_antenna_controller(self) -> JSONResponse | AntennaController:
        """Retrieve the antenna controller or raise HTTP error if uninitialized."""
        if self.__antenna_controller is None:
            return JSONResponse(status_code=503, content=f"{self._('rest.antenna.controller.is.not.initialized.error')}")
        return self.__antenna_controller

    def __get_astro_calculator(self) -> JSONResponse | AstronomicalCalculator:
        """Retrieve the astronomical calculator or raise HTTP error if not configured."""
        if self.__astro_calculator is None or self.__current_observer_location is None:
            return JSONResponse(status_code=503, content=f"{self._('rest.antenna.controller.is.not.configured.error')}")
        return self.__astro_calculator

    def __get_astro_tracker(self) -> JSONResponse | AstronomicalTracker:
        """Retrieve the astronomical tracker or raise HTTP error if not configured."""
        if self.__astro_tracker is None:
            return JSONResponse(status_code=503, content=f"{self._('rest.antenna.tracker.is.not.configured.error')}")
        return self.__astro_tracker

    async def __continuous_tracking_task(self, tracking_config: TrackingConfigModel):
        """Task for continuous tracking of an astronomical object."""
        self.__logger.info(f"Starting continuous tracking of object: {tracking_config.object_name}")

        try:
            tracker = self.__get_astro_tracker()
            controller = self.__get_antenna_controller()

            # Create a tracking function for the specified object
            if tracking_config.object_type == AstronomicalObjectType.SUN:
                track_function = tracker.track_sun()
            elif tracking_config.object_type == AstronomicalObjectType.MOON:
                track_function = tracker.track_moon()
            elif tracking_config.object_type in [
                AstronomicalObjectType.MERCURY,
                AstronomicalObjectType.VENUS,
                AstronomicalObjectType.MARS,
                AstronomicalObjectType.JUPITER,
                AstronomicalObjectType.SATURN,
                AstronomicalObjectType.URANUS,
                AstronomicalObjectType.NEPTUNE
            ]:
                track_function = tracker.track_planet(tracking_config.object_type)
            elif tracking_config.object_type == AstronomicalObjectType.STAR:
                track_function = tracker.track_star(tracking_config.object_name)
            elif tracking_config.object_type == AstronomicalObjectType.CUSTOM:
                return JSONResponse(status_code=400, content=f"{self._('rest.antenna.objects.need.coordinates.error')}")
            else:
                # Attempt to auto-detect type by name
                obj_name = tracking_config.object_name.lower()
                if obj_name == "sun":
                    track_function = tracker.track_sun()
                elif obj_name == "moon":
                    track_function = tracker.track_moon()
                elif obj_name in ["mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune"]:
                    planet_type = AstronomicalObjectType(obj_name)
                    track_function = tracker.track_planet(planet_type)
                else:
                    track_function = tracker.track_star(tracking_config.object_name)

            while self.__tracking_active:
                try:
                    # Get current position of object
                    target_position = track_function()

                    if target_position is None:
                        self.__logger.warning(f"Object {tracking_config.object_name} is out of range")
                        break

                    self.__logger.info(
                        f"Tracking {tracking_config.object_name}: Az={target_position.azimuth:.2f}°, El={target_position.elevation:.2f}°"
                    )

                    # Move antenna to new position at each interval
                    controller.move_to(target_position)
                    self.__logger.info(
                        f"Antenna moved to position: Az={target_position.azimuth:.2f}°, El={target_position.elevation:.2f}°"
                    )

                    await asyncio.sleep(tracking_config.update_interval)

                except Exception as e:
                    self.__logger.error(f"Error during tracking: {e}")
                    await asyncio.sleep(5)  # shorter pause on error

        except Exception as e:
            self.__logger.error(f"Critical tracking error: {e}")
        finally:
            self.__tracking_active = False
            self.__logger.info(f"Tracking ended for object: {tracking_config.object_name}")
