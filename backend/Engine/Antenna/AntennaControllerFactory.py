import logging
from typing import Optional

from Engine.Antenna.Constants import DEFAULT_CALIBRATION_FILE, DEFAULT_BAUDRATE
from Engine.Antenna.AntennaController import AntennaController
from Engine.Antenna.AntennaControllerService import AntennaControllerService
from Engine.Antenna.AntennaControllerHelper import AntennaLimits
from Engine.Antenna.Motor import MotorConfig, RotctlMotorDriver, SimulatedMotorDriver
from LanguageHelper import LanguageHelper


class AntennaControllerFactory:
    """Factory for creating antenna controllers."""

    __logger = logging.getLogger(__name__)

    def __init__(self, languageHelper: LanguageHelper):
        self.__languageHelper = languageHelper
        self._ = self.__languageHelper.getTranslatedMessage("Antenna")
        self.__antennaControllerService = AntennaControllerService(self.__languageHelper)

    def create_spid_controller(self, port: Optional[str] = None, baudrate: int = DEFAULT_BAUDRATE,
                               motor_config: Optional[MotorConfig] = None, limits: Optional[AntennaLimits] = None,
                               calibration_file: str = DEFAULT_CALIBRATION_FILE) -> AntennaController:
        """Creates a controller with an SPID driver."""

        if port is None:  # If no port is provided, use automatic selection
            port = self.__antennaControllerService.get_best_spid_port()
            self.__logger.info(f"Automatically selected port: {port}")
        else:
            # Check if the provided port is available
            port = self.__antennaControllerService.get_best_spid_port(preferred_port=port)

        motor_driver = RotctlMotorDriver(self.__antennaControllerService,self.__languageHelper,port,baudrate)
        motor_config = motor_config or MotorConfig()

        return AntennaController(motor_driver, motor_config, self.__languageHelper, limits, calibration_file=calibration_file)

    def create_simulator_controller(self, simulation_speed: float = 1000.0,
                                    motor_config: Optional[MotorConfig] = None, limits: Optional[AntennaLimits] = None,
                                    calibration_file: str = DEFAULT_CALIBRATION_FILE) -> AntennaController:
        """Creates a controller using a simulator."""

        motor_driver = SimulatedMotorDriver(self.__languageHelper, simulation_speed)
        motor_config = motor_config or MotorConfig()

        return AntennaController(motor_driver, motor_config, self.__languageHelper, limits, calibration_file=calibration_file)
