import time
from typing import Tuple

class SimulatedMotorDriver(MotorDriver):
    """Symulator sterownika silnika do testów - operuje bezpośrednio na stopniach"""

    def __init__(self, simulation_speed: float = 10.0):
        self.simulation_speed = simulation_speed  # stopnie/s
        self.current_azimuth = 0.0  # stopnie
        self.current_elevation = 0.0  # stopnie (horyzont)
        self.target_azimuth = 0.0
        self.target_elevation = 0.0
        self.connected = False
        self.is_moving_flag = False
        self.last_move_time = time.time()

    def connect(self) -> None:
        """Symuluje nawiązanie połączenia"""
        self.connected = True
        logger.info("Połączono z symulatorem sterownika")

    def disconnect(self) -> None:
        """Symuluje rozłączenie"""
        self.connected = False
        logger.info("Rozłączono z symulatorem sterownika")

    def move_to_position(self, azimuth: float, elevation: float) -> None:
        """Symuluje ruch do pozycji w stopniach"""
        if not self.connected:
            raise CommunicationError("Symulator nie jest połączony")

        self.target_azimuth = azimuth
        self.target_elevation = elevation
        self.is_moving_flag = True
        self.last_move_time = time.time()

        logger.info(f"Symulator: Ruch do pozycji Az={azimuth}°, El={elevation}°")

    def get_position(self) -> Tuple[float, float]:
        """Zwraca aktualną pozycję w stopniach z symulacją ruchu"""
        if not self.connected:
            raise CommunicationError("Symulator nie jest połączony")

        if self.is_moving_flag:
            self._simulate_movement()

        return self.current_azimuth, self.current_elevation

    def _simulate_movement(self) -> None:
        """Symuluje płynny ruch anteny w stopniach"""
        current_time = time.time()
        dt = current_time - self.last_move_time
        self.last_move_time = current_time

        # Oblicz maksymalny ruch w tym kroku czasowym (stopnie)
        max_move = self.simulation_speed * dt

        # Ruch azymutu
        az_diff = self.target_azimuth - self.current_azimuth
        if abs(az_diff) <= max_move:
            self.current_azimuth = self.target_azimuth
        else:
            self.current_azimuth += max_move if az_diff > 0 else -max_move

        # Ruch elewacji
        el_diff = self.target_elevation - self.current_elevation
        if abs(el_diff) <= max_move:
            self.current_elevation = self.target_elevation
        else:
            self.current_elevation += max_move if el_diff > 0 else -max_move

        # Sprawdź czy osiągnięto cel
        if (
            abs(self.current_azimuth - self.target_azimuth) < 0.1
            and abs(self.current_elevation - self.target_elevation) < 0.1
        ):
            self.is_moving_flag = False
            logger.debug("Symulator: Ruch zakończony")

    def stop(self) -> None:
        """Symuluje zatrzymanie ruchu"""
        self.is_moving_flag = False
        # Ustaw cele na aktualną pozycję
        self.target_azimuth = self.current_azimuth
        self.target_elevation = self.current_elevation
        logger.info("Symulator: Ruch zatrzymany")

    def is_moving(self) -> bool:
        """Sprawdza czy symulator jest w ruchu"""
        if self.is_moving_flag:
            self._simulate_movement()
        return self.is_moving_flag