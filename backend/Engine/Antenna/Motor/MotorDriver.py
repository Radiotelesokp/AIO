from abc import ABC, abstractmethod
from typing import Tuple

class MotorDriver(ABC):
    """Abstract motor driver class"""

    @abstractmethod
    def connect(self) -> None:
        """Establishes connection with the driver"""

    @abstractmethod
    def disconnect(self) -> None:
        """Disconnects from the driver"""

    @abstractmethod
    def move_to_position(self, azimuth: float, elevation: float) -> None:
        """Moves the antenna to the specified position in degrees"""

    @abstractmethod
    def get_position(self) -> Tuple[float, float]:
        """Returns the current position in degrees"""

    @abstractmethod
    def stop(self) -> None:
        """Stops all motors"""

    @abstractmethod
    def is_moving(self) -> bool:
        """Checks if the motors are moving"""