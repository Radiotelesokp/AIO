from abc import ABC, abstractmethod
from typing import Tuple

class MotorDriver(ABC):
    """Abstrakcyjna klasa sterownika silnika"""

    @abstractmethod
    def connect(self) -> None:
        """Nawiązuje połączenie z sterownikiem"""

    @abstractmethod
    def disconnect(self) -> None:
        """Rozłącza się ze sterownikiem"""

    @abstractmethod
    def move_to_position(self, azimuth: float, elevation: float) -> None:
        """Przesuwa anteny do pozycji w stopniach"""

    @abstractmethod
    def get_position(self) -> Tuple[float, float]:
        """Zwraca aktualną pozycję w stopniach"""

    @abstractmethod
    def stop(self) -> None:
        """Zatrzymuje wszystkie silniki"""

    @abstractmethod
    def is_moving(self) -> bool:
        """Sprawdza czy silniki się poruszają"""