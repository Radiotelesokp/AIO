import logging
from typing import Optional

from backend.Engine.Antenna import DEFAULT_CALIBRATION_FILE, DEFAULT_BAUDRATE, AntennaController, AntennaControlerSerivce
from backend.Engine.Antenna.AntennaControllerHelper import AntennaLimits
from backend.Engine.Antenna.Motor import MotorConfig, RotctlMotorDriver, SimulatedMotorDriver


class AntennaControllerFactory:
    """Factory do tworzenia kontrolerów anteny"""
    
    __logger = logging.getLogger(__name__)
    def __init__(self):
        __antennaControlerSerivce = AntennaControlerSerivce()

    @staticmethod
    def create_spid_controller(self,
        port: Optional[str] = None,
        baudrate: int = DEFAULT_BAUDRATE,
        motor_config: Optional[MotorConfig] = None,
        limits: Optional[AntennaLimits] = None,
        calibration_file: str = DEFAULT_CALIBRATION_FILE,
    ) -> AntennaController:
        """Tworzy kontroler z sterownikiem SPID"""
        # Jeśli port nie został podany, użyj inteligentnego wyboru
        if port is None:
            port = self.__antennaControlerSerivce.get_best_spid_port()
            self.__logger.info(f"Automatycznie wybrano port: {port}")
        else:
            # Sprawdź czy podany port jest dostępny
            port = self.__antennaControlerSerivce.get_best_spid_port(preferred_port=port)

        motor_driver = RotctlMotorDriver(port, baudrate)
        motor_config = motor_config or MotorConfig()

        return AntennaController(motor_driver, motor_config, limits, calibration_file=calibration_file)

    @staticmethod
    def create_simulator_controller(self,
        simulation_speed: float = 1000.0,
        motor_config: Optional[MotorConfig] = None,
        limits: Optional[AntennaLimits] = None,
        calibration_file: str = DEFAULT_CALIBRATION_FILE,
    ) -> AntennaController:
        """Tworzy kontroler z symulatorem"""
        motor_driver = SimulatedMotorDriver(simulation_speed)
        motor_config = motor_config or MotorConfig()

        return AntennaController(motor_driver, motor_config, limits, calibration_file=calibration_file)