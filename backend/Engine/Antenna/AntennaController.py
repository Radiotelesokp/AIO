import logging
import threading
import time
from typing import Optional, Dict, Any, Callable

from backend.Engine.Antenna import DEFAULT_CALIBRATION_FILE
from backend.Engine.Antenna.AntennaControllerHelper import AntennaLimits, AntennaState, AntennaError, SafetyError, \
    PositionError
from backend.Engine.Antenna.Motor import MotorDriver, MotorConfig
from backend.Engine.Antenna.Position import Position, PositionCalibration


class AntennaController:
    """Główny kontroler anteny radioteleskopu"""
    __logger = logging.getLogger(__name__)

    def __init__(
            self,
            motor_driver: MotorDriver,
            motor_config: MotorConfig,
            limits: Optional[AntennaLimits] = None,
            update_callback: Optional[Callable] = None,
            position_calibration: Optional[PositionCalibration] = None,
            calibration_file: str = DEFAULT_CALIBRATION_FILE,
    ):
        self.motor_driver = motor_driver
        self.motor_config = motor_config
        self.update_callback = update_callback
        self.calibration_file = calibration_file

        # Wczytaj kalibrację z pliku lub użyj podanej
        if position_calibration is not None:
            self.position_calibration = position_calibration
        else:
            self.position_calibration = PositionCalibration.load_from_file(
                self.calibration_file
            )

        # Ustaw limity - używaj limitów z kalibracji, jeśli nie podano innych
        if limits is not None:
            self.limits = limits
            self.__logger.info("Używam podanych limitów bezpieczeństwa")
        else:
            self.limits = self.position_calibration.get_antenna_limits()
            self.__logger.info("Używam limitów bezpieczeństwa z pliku kalibracji")

        self.state = AntennaState.IDLE
        self.current_position = Position(0.0, 0.0)
        self.target_position: Optional[Position] = None

        self._monitoring_thread: Optional[threading.Thread] = None
        self._monitoring_active = False
        self._stop_monitoring = threading.Event()

    def initialize(self) -> None:
        """Inicjalizuje system anteny"""
        try:
            self.motor_driver.connect()
            self._start_monitoring()
            self.state = AntennaState.IDLE
            self.__logger.info("System anteny zainicjalizowany")
        except Exception as e:
            self.state = AntennaState.ERROR
            raise AntennaError(f"Błąd inicjalizacji: {e}")

    def shutdown(self) -> None:
        """Bezpieczne wyłączenie systemu"""
        self.stop()
        self._stop_monitoring.set()
        if self._monitoring_thread and self._monitoring_thread.is_alive():
            self._monitoring_thread.join()
        self.motor_driver.disconnect()
        self.__logger.info("System anteny wyłączony")

    def _start_monitoring(self) -> None:
        """Uruchamia wątek monitorowania pozycji"""
        self._monitoring_active = True
        self._stop_monitoring.clear()
        self._monitoring_thread = threading.Thread(target=self._monitor_position)
        self._monitoring_thread.daemon = True
        self._monitoring_thread.start()

    def _monitor_position(self) -> None:
        """Monitoruje pozycję anteny w osobnym wątku"""
        consecutive_errors = 0
        max_consecutive_errors = 3

        while not self._stop_monitoring.is_set():
            try:
                # Wszystkie sterowniki teraz zwracają bezpośrednio stopnie
                azimuth, elevation = self.motor_driver.get_position()
                self.current_position = Position(azimuth, elevation)

                # Sprawdź czy ruch się zakończył
                if (
                        self.state == AntennaState.MOVING
                        and not self.motor_driver.is_moving()
                ):
                    self.state = AntennaState.IDLE
                    self.__logger.info(f"Ruch zakończony. Pozycja: {self.current_position}")

                # Wywołaj callback jeśli zdefiniowany
                if self.update_callback:
                    self.update_callback(self.current_position, self.state)

                # Zeruj licznik błędów po udanym odczycie
                consecutive_errors = 0

            except Exception as e:
                consecutive_errors += 1
                self.__logger.error(f"Błąd monitorowania: {e}")

                # Jeśli wystąpiło zbyt wiele błędów pod rząd, ustaw stan błędu
                if consecutive_errors >= max_consecutive_errors:
                    self.state = AntennaState.ERROR
                    self.__logger.error(
                        f"Zbyt wiele błędów monitorowania pod rząd ({consecutive_errors})"
                    )

                # Krótka pauza po błędzie
                time.sleep(0.2)

            time.sleep(0.5)  # Aktualizacja co 500ms

    def _validate_position(self, position: Position) -> None:
        """Waliduje pozycję względem limitów mechanicznych"""
        if not (self.limits.min_azimuth <= position.azimuth <= self.limits.max_azimuth):
            raise SafetyError(
                f"Azymut {position.azimuth}° poza limitami "
                f"({self.limits.min_azimuth}°-{self.limits.max_azimuth}°)"
            )

        if not (
                self.limits.min_elevation <= position.elevation <= self.limits.max_elevation
        ):
            raise SafetyError(
                f"Elewacja {position.elevation}° poza limitami "
                f"({self.limits.min_elevation}°-{self.limits.max_elevation}°)"
            )

    def move_to(self, position: Position) -> None:
        """Przesuwa antenę do zadanej pozycji (z uwzględnieniem kalibracji)"""
        if self.state == AntennaState.ERROR:
            raise AntennaError("System w stanie błędu - nie można wykonać ruchu")

        # Aplikuj kalibrację do zadanej pozycji
        calibrated_position = self.position_calibration.apply_calibration(position)

        # Waliduj skalibrowaną pozycję
        self._validate_position(calibrated_position)

        try:
            self.target_position = (
                position  # Zapisz oryginalną pozycję (bez kalibracji)
            )
            self.state = AntennaState.MOVING

            # Wszystkie sterowniki teraz przyjmują stopnie
            self.motor_driver.move_to_position(
                calibrated_position.azimuth, calibrated_position.elevation
            )

            self.__logger.info(
                f"Rozpoczęto ruch do pozycji: {position} (skalibrowana: {calibrated_position})"
            )

        except Exception as e:
            self.state = AntennaState.ERROR
            raise PositionError(f"Błąd podczas ruchu: {e}")

    def get_current_position(self, apply_reverse_calibration: bool = True) -> Position:
        """Zwraca aktualną pozycję anteny"""
        if apply_reverse_calibration:
            # Zwróć pozycję z odwróconą kalibracją (rzeczywista pozycja logiczna)
            return self.position_calibration.reverse_calibration(self.current_position)
        else:
            # Zwróć surową pozycję z sensora
            return self.current_position

    def set_position_calibration(
            self,
            calibration: PositionCalibration,
            save_to_file: bool = True,
            update_limits: bool = True,
    ) -> None:
        """Ustawia kalibrację pozycji"""
        self.position_calibration = calibration

        # Zaktualizuj limity na podstawie kalibracji jeśli wymagane
        if update_limits:
            self.limits = calibration.get_antenna_limits()
            self.__logger.info("Limity bezpieczeństwa zaktualizowane na podstawie kalibracji")

        if save_to_file:
            try:
                calibration.save_to_file(self.calibration_file)
                self.__logger.info("Kalibracja została automatycznie zapisana do pliku")
            except Exception as e:
                self.__logger.warning(f"Nie udało się zapisać kalibracji do pliku: {e}")

        self.__logger.info(
            f"Ustawiono kalibrację pozycji: offset_az={calibration.azimuth_offset}°, "
            f"offset_el={calibration.elevation_offset}°"
        )
        self.__logger.info(
            f"Limity: az({calibration.min_azimuth}°-{calibration.max_azimuth}°), "
            f"el({calibration.min_elevation}°-{calibration.max_elevation}°)"
        )

    def save_calibration(self, filepath: Optional[str] = None) -> None:
        """Zapisuje aktualną kalibrację do pliku"""
        file_to_use = filepath or self.calibration_file
        self.position_calibration.save_to_file(file_to_use)
        self.__logger.info(f"Kalibracja zapisana do {file_to_use}")

    def load_calibration(
            self, filepath: Optional[str] = None, update_limits: bool = True
    ) -> None:
        """Wczytuje kalibrację z pliku"""
        file_to_use = filepath or self.calibration_file
        self.position_calibration = PositionCalibration.load_from_file(file_to_use)

        # Zaktualizuj limity na podstawie wczytanej kalibracji
        if update_limits:
            self.limits = self.position_calibration.get_antenna_limits()
            self.__logger.info(
                "Limity bezpieczeństwa zaktualizowane na podstawie wczytanej kalibracji"
            )

        self.__logger.info(f"Kalibracja wczytana z {file_to_use}")

    def reset_calibration(
            self, save_to_file: bool = True, update_limits: bool = True
    ) -> None:
        """Resetuje kalibrację do wartości domyślnych"""
        self.position_calibration = PositionCalibration()

        # Zaktualizuj limity na podstawie domyślnej kalibracji
        if update_limits:
            self.limits = self.position_calibration.get_antenna_limits()
            self.__logger.info("Limity bezpieczeństwa zresetowane do wartości domyślnych")

        if save_to_file:
            try:
                self.save_calibration()
                self.__logger.info("Zresetowana kalibracja została zapisana do pliku")
            except Exception as e:
                self.__logger.warning(f"Nie udało się zapisać zresetowanej kalibracji: {e}")

        self.__logger.info("Kalibracja została zresetowana do wartości domyślnych")

    def calibrate_azimuth_reference(
            self,
            current_azimuth: float = None,
            save_to_file: bool = True,
    ) -> None:
        """Kalibruje referencję azymutu"""
        if current_azimuth is None:
            current_azimuth = self.current_position.azimuth

        # Oblicz offset potrzebny aby current_azimuth stał się 0°
        offset = -current_azimuth
        self.position_calibration.azimuth_offset = offset

        if save_to_file:
            try:
                self.save_calibration()
                self.__logger.info("Kalibracja azymutu została zapisana do pliku")
            except Exception as e:
                self.__logger.warning(f"Nie udało się zapisać kalibracji azymutu: {e}")

        self.__logger.info(f"Skalibrowano azymut: offset={offset}°")

    def stop(self) -> None:
        """Zatrzymuje ruch anteny"""
        try:
            self.motor_driver.stop()
            self.state = AntennaState.STOPPED
            self.target_position = None
            self.__logger.info("Ruch anteny zatrzymany")
        except Exception as e:
            self.state = AntennaState.ERROR
            raise AntennaError(f"Błąd zatrzymania: {e}")

    def calibrate(self) -> None:
        """Kalibruje pozycję anteny (powrót do pozycji domowej)"""
        self.__logger.info("Rozpoczęcie kalibracji...")
        self.state = AntennaState.CALIBRATING

        # Powrót do pozycji 0,0
        home_position = Position(0.0, 0.0)
        self.move_to(home_position)

        # Czekaj na zakończenie kalibracji
        while self.state == AntennaState.MOVING:
            time.sleep(0.1)

        self.state = AntennaState.IDLE
        self.__logger.info("Kalibracja zakończona")

    def get_status(self) -> Dict[str, Any]:
        """Zwraca pełny status anteny"""
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
        """Resetuje stan błędu kontrolera"""
        if self.state == AntennaState.ERROR:
            self.state = AntennaState.IDLE
            self.__logger.info("Stan błędu został zresetowany")

    def wait_for_movement(self, timeout: float = 90.0) -> None:
        """
        Czeka na zakończenie ruchu z timeoutem.
        Sprawdza zarówno stan kontrolera jak i rzeczywisty ruch anteny.

        Args:
            timeout: Maksymalny czas oczekiwania w sekundach

        Raises:
            TimeoutError: Gdy przekroczono czas oczekiwania
        """

        start_time = time.time()
        last_movement_time = start_time
        prev_position = None

        while True:
            current_time = time.time()
            elapsed_time = current_time - start_time

            try:
                # Pobierz aktualną pozycję
                current_position = self.current_position

                # Sprawdź czy antena się porusza (porównaj z poprzednią pozycją)
                if prev_position is not None:
                    az_moved = abs(current_position.azimuth - prev_position.azimuth)
                    if az_moved > 180:  # Uwzględnij przejście przez 0°
                        az_moved = 360 - az_moved
                    el_moved = abs(current_position.elevation - prev_position.elevation)

                    # Jeśli antena się porusza (więcej niż 0.2°), zaktualizuj czas ostatniego ruchu
                    if az_moved > 0.2 or el_moved > 0.2:
                        last_movement_time = current_time
                        self.__logger.debug(f"Wykryto ruch anteny: dAz={az_moved:.1f}°, dEl={el_moved:.1f}°")

                # Sprawdź stan kontrolera - jeśli nie jest w ruchu i pozycja się stabilizowała
                time_since_movement = current_time - last_movement_time
                if (self.state != AntennaState.MOVING and
                        time_since_movement > 3.0):  # 3 sekundy bez ruchu dla lepszej stabilności
                    self.__logger.debug(f"Ruch zakończony - stan: {self.state}, brak ruchu przez {time_since_movement:.1f}s")
                    break

                # Sprawdź timeout - ale tylko jeśli antena nie porusza się przez ostatnie 10 sekund
                if elapsed_time > timeout and time_since_movement > 10.0:
                    self.stop()
                    raise TimeoutError(
                        f"Przekroczono czas oczekiwania na ruch ({timeout}s), brak ruchu przez {time_since_movement:.1f}s"
                    )

                # Zapisz pozycję dla następnej iteracji
                prev_position = current_position
                time.sleep(0.5)

            except Exception as e:
                if isinstance(e, TimeoutError):
                    raise
                self.__logger.warning(f"Błąd podczas sprawdzania ruchu: {e}")
                time.sleep(0.5)