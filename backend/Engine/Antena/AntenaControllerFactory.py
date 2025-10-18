from typing import Optional

from backend.Engine.Antena.AntenaController import AntennaLimits, AntenaController
from backend.Engine.Antena.Motor.MotorConfig import MotorConfig
from backend.Engine.Antena.RotctlMotorDriver import RotctlMotorDriver
from backend.Engine.Antena.SimulatedMotorDriver import SimulatedMotorDriver


class AntennaControllerFactory:
    """Factory do tworzenia kontrolerów anteny"""

    @staticmethod
    def create_spid_controller(
        port: Optional[str] = None,
        baudrate: int = DEFAULT_BAUDRATE,
        motor_config: Optional[MotorConfig] = None,
        limits: Optional[AntennaLimits] = None,
        calibration_file: str = DEFAULT_CALIBRATION_FILE,
    ) -> AntenaController:
        """Tworzy kontroler z sterownikiem SPID"""
        # Jeśli port nie został podany, użyj inteligentnego wyboru
        if port is None:
            port = get_best_spid_port()
            logger.info(f"Automatycznie wybrano port: {port}")
        else:
            # Sprawdź czy podany port jest dostępny
            port = get_best_spid_port(preferred_port=port)

        motor_driver = RotctlMotorDriver(port, baudrate)
        motor_config = motor_config or MotorConfig()

        return AntennaController(
            motor_driver, motor_config, limits, calibration_file=calibration_file
        )

    @staticmethod
    def create_simulator_controller(
        simulation_speed: float = 1000.0,
        motor_config: Optional[MotorConfig] = None,
        limits: Optional[AntennaLimits] = None,
        calibration_file: str = DEFAULT_CALIBRATION_FILE,
    ) -> AntennaController:
        """Tworzy kontroler z symulatorem"""
        motor_driver = SimulatedMotorDriver(simulation_speed)
        motor_config = motor_config or MotorConfig()

        return AntennaController(
            motor_driver, motor_config, limits, calibration_file=calibration_file
        )