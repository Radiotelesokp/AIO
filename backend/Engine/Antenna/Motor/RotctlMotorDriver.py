import logging
import time
from typing import Tuple

from backend.Engine.Antenna import DEFAULT_BAUDRATE
from backend.Engine.Antenna.AntennaControlerSerivce import sprawdz_rotctl, rotctl_odczytaj_pozycje,\
rotctl_ustaw_pozycje, rotctl_zatrzymaj_rotor
from backend.Engine.Antenna.AntennaControllerHelper import CommunicationError, PositionError
from backend.Engine.Antenna.Motor import MotorDriver


class RotctlMotorDriver(MotorDriver):
    __logger = logging.getLogger(__name__)
    """Sterownik silnika komunikujący się przez rotctl (Hamlib) z protokołem SPID"""

    def __init__(self, port: str, baudrate: int = DEFAULT_BAUDRATE):
        self.port = port
        self.baudrate = baudrate
        self.connected = False
        self.current_azimuth = 0.0
        self.current_elevation = 0.0
        self.target_azimuth = 0.0
        self.target_elevation = 0.0
        self.is_moving_flag = False

    def connect(self) -> None:
        """Sprawdza dostępność rotctl i portu"""
        try:
            if not sprawdz_rotctl():
                raise CommunicationError("rotctl (Hamlib) nie jest dostępne w systemie")

            # Test połączenia - spróbuj odczytać pozycję
            self.current_azimuth, self.current_elevation = rotctl_odczytaj_pozycje(
                self.port, self.baudrate
            )
            self.connected = True
            self.__logger.info(
                f"Połączono z kontrolerem SPID przez rotctl na porcie {self.port} (baudrate: {self.baudrate})"
            )
            self.__logger.info(
                f"Aktualna pozycja: Az={self.current_azimuth:.1f}°, El={self.current_elevation:.1f}°"
            )

        except Exception as e:
            self.__logger.error(f"Błąd połączenia z SPID przez rotctl: {e}")
            raise CommunicationError(f"Nie można nawiązać połączenia przez rotctl: {e}")

    def disconnect(self) -> None:
        """Rozłącza połączenie - rotctl nie wymaga jawnego rozłączania"""
        self.connected = False
        self.__logger.info("Rozłączono z kontrolerem SPID (rotctl)")

    def get_position(self) -> Tuple[float, float]:
        """Odczytuje aktualną pozycję anteny w stopniach"""
        if not self.connected:
            raise CommunicationError("Sterownik rotctl nie jest połączony")

        try:
            self.current_azimuth, self.current_elevation = rotctl_odczytaj_pozycje(
                self.port, self.baudrate
            )
            return self.current_azimuth, self.current_elevation

        except Exception as e:
            self.__logger.error(f"Błąd odczytu pozycji przez rotctl: {e}")
            raise CommunicationError(f"Nie można odczytać pozycji przez rotctl: {e}")

    def move_to_position(self, azimuth: float, elevation: float) -> None:
        """Przesuwa antenę do zadanej pozycji w stopniach"""
        if not self.connected:
            raise CommunicationError("Sterownik rotctl nie jest połączony")

        # Walidacja zakresu
        if not (0 <= azimuth <= 360):
            raise PositionError(f"Azymut poza zakresem: {azimuth}° (oczekiwano 0-360°)")

        try:
            self.target_azimuth = azimuth
            self.target_elevation = elevation
            self.is_moving_flag = True

            self.__logger.info(
                f"Rotctl: Ustawianie pozycji Az={azimuth:.1f}°, El={elevation:.1f}°"
            )

            # Dodatkowy delay przed wysłaniem komendy
            time.sleep(0.2)

            response = rotctl_ustaw_pozycje(
                self.port, azimuth, elevation, self.baudrate
            )

            self.__logger.info(f"Rotctl: Komenda wysłana. Odpowiedź: {response}")

        except Exception as e:
            self.is_moving_flag = False
            self.__logger.error(f"Błąd podczas ruchu przez rotctl: {e}")
            raise CommunicationError(f"Nie można przesunąć anteny przez rotctl: {e}")

    def stop(self) -> None:
        """Zatrzymuje ruch anteny"""
        if not self.connected:
            raise CommunicationError("Sterownik rotctl nie jest połączony")

        try:
            self.__logger.info("Rotctl: Zatrzymywanie ruchu anteny")
            response = rotctl_zatrzymaj_rotor(self.port, self.baudrate)
            self.is_moving_flag = False
            self.__logger.info(f"Rotctl: Ruch zatrzymany. Odpowiedź: {response}")

        except Exception as e:
            self.__logger.error(f"Błąd podczas zatrzymywania przez rotctl: {e}")
            raise CommunicationError(f"Nie można zatrzymać anteny przez rotctl: {e}")

    def is_moving(self) -> bool:
        """
        Sprawdza czy antena się porusza przez porównanie aktualnej i docelowej pozycji.

        Nota: rotctl nie zapewnia bezpośredniego sprawdzenia statusu ruchu,
        więc sprawdzamy czy pozycja jest bliska docelowej.
        """
        if not self.is_moving_flag:
            return False

        try:
            current_az, current_el = self.get_position()

            # Tolerancja pozycji (1 stopień)
            az_diff = abs(current_az - self.target_azimuth)
            el_diff = abs(current_el - self.target_elevation)

            # Uwzględnij przejście przez 0°/360° dla azymutu
            if az_diff > 180:
                az_diff = 360 - az_diff

            is_at_target = az_diff < 1.0 and el_diff < 1.0

            if is_at_target:
                self.is_moving_flag = False
                self.__logger.info(
                    f"Rotctl: Pozycja docelowa osiągnięta Az={current_az:.1f}°, El={current_el:.1f}°"
                )

            return not is_at_target

        except Exception as e:
            self.__logger.warning(f"Błąd sprawdzenia ruchu przez rotctl: {e}")
            # W razie błędu zakładamy że ruch się zakończył
            self.is_moving_flag = False
            return False