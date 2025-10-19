"""
Biblioteka do sterowania silnikiem anteny radioteleskopu
Protokół komunikacji: Hamlib rotctl

Główna biblioteka zawierająca kompletny system sterowania anteną radioteleskopu.
Używa biblioteki Hamlib (rotctl) do komunikacji z kontrolerem SPID MD-01/02/03.
Obejmuje sterownik rotctl, kontroler pozycji, monitorowanie w czasie
rzeczywistym oraz kompleksową obsługę błędów i limitów bezpieczeństwa.

Autor: Aleks Czarnecki
"""

import logging
import time
import subprocess
import re
from typing import Optional, Any

from backend.Engine.Antenna import DEFAULT_ROTCTL_MODEL, DEFAULT_TIMEOUT, DEFAULT_BAUDRATE, DEFAULT_SPID_PORT


class AntennaControllerService():
    __logger = logging.getLogger(__name__)

    def check_rotctl(self) -> bool:
        """ Check availability of rotctl in OS."""
        try:
            result = subprocess.run(["rotctl", "--version"], capture_output=True,
                text=True, timeout=DEFAULT_TIMEOUT, check=False)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False


    def set_position_rotctl(self, port: str, az: float, el: float,
                            speed: int = DEFAULT_BAUDRATE, retry_count: int = 2,
                            model: str = DEFAULT_ROTCTL_MODEL) -> str:
        """
        Ustawia pozycję rotatora SPID za pomocą rotctl (Hamlib).

        Args:
            port: Port szeregowy (np. '/dev/tty.usbserial-A10PDNT7')
            az: Azymut w stopniach (0-360)
            el: Elewacja w stopniach (-90 do +90)
            speed: Prędkość portu szeregowego
            retry_count: Liczba ponownych prób w przypadku błędu
            model: Rotctl model

        Returns:
            Odpowiedź rotctl jako string

        Raises:
            RuntimeError: Jeśli komenda się nie powiodła po wszystkich próbach
        """
        if not self.check_rotctl():
            raise RuntimeError("rotctl (Hamlib) nie jest dostępne w systemie")

        command = f"P {az % 360:.1f} {el:.1f}\n"
        normalized_az = az % 360

        # check limits # TODO: that constant values move to helper class or check AntennaLimits
        if el < -90.0 or el > 90.0:
            raise RuntimeError(f"Elewacja {el:.1f}° poza dozwolonym zakresem (-90° do +90°)")
        self.__logger.info(f"Rotctl: Wysyłam komendę pozycji - Az={normalized_az:.1f}°, El={el:.1f}°")

        for attempt in range(retry_count + 1):
            proc = subprocess.Popen(
                ["rotctl", "-m", model, "-r", port, "-s", str(speed), "-"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            try:
                stdout, stderr = proc.communicate(input=command, timeout=15)

                if proc.returncode == 0:
                    self.__logger.debug(
                        f"Rotctl ustaw pozycję Az={normalized_az:.1f}°, El={el:.1f}° - odpowiedź: {stdout.strip()}"
                    )
                    return stdout.strip()
                else:
                    error_msg = stderr.strip() if stderr.strip() else stdout.strip()
                    if attempt < retry_count:
                        self.__logger.warning(
                            f"Próba {attempt + 1} nieudana, kod: {proc.returncode}, błąd: '{error_msg}', ponawiam..."
                        )
                        time.sleep(1)
                    else:
                        raise RuntimeError(
                            f"Błąd rotctl podczas ustawiania pozycji Az={normalized_az:.1f}°, El={el:.1f}°: kod {proc.returncode}, błąd: '{error_msg}'"
                        )

            except subprocess.TimeoutExpired:
                proc.kill()
                if attempt < retry_count:
                    self.__logger.warning(f"Timeout podczas próby {attempt + 1}, ponawiam...")
                    time.sleep(1)
                else:
                    raise RuntimeError("Timeout podczas komunikacji z rotctl po wszystkich próbach")

            except Exception as e:
                if attempt < retry_count:
                    self.__logger.warning(f"Błąd podczas próby {attempt + 1}: {e}, ponawiam...")
                    time.sleep(1)
                    continue
                else:
                    raise RuntimeError(f"Błąd podczas komunikacji z rotctl: {e}")
        return ""

    def read_position_rotctl(self, port: str, speed: int = DEFAULT_BAUDRATE, retry_count: int = 2,
                             model: str = DEFAULT_ROTCTL_MODEL) -> tuple[Any, Any] | tuple[float, float] | None:
        """
        Odczytuje aktualną pozycję rotatora SPID za pomocą rotctl.

        Args:
            port: Port szeregowy
            speed: Prędkość portu szeregowego
            retry_count: Liczba ponownych prób w przypadku błędu
            model: Rotctl model

        Returns:
            Tuple (azymut, elewacja) w stopniach

        Raises:
            RuntimeError: Jeśli odczyt się nie powiódł po wszystkich próbach
        """
        if not self.check_rotctl():
            raise RuntimeError("rotctl (Hamlib) nie jest dostępne w systemie")

        for attempt in range(retry_count + 1):
            proc = subprocess.Popen(
                ["rotctl", "-m", model, "-r", port, "-s", str(speed), "-"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            try:
                stdout, stderr = proc.communicate(input="p\n", timeout=15)

                if proc.returncode == 0:
                    # Parsowanie odpowiedzi rotctl
                    lines = stdout.strip().split("\n")
                    values = []

                    for line in lines:
                        line = line.strip()
                        if line and not line.startswith("p "):
                            try:
                                values.append(float(line))
                            except ValueError:
                                # Sprawdź czy linia zawiera wartość po "p "
                                if line.startswith("p "):
                                    try:
                                        values.append(float(line[2:]))
                                    except ValueError:
                                        continue

                    if len(values) >= 2:
                        az, el = values[0], values[1]
                        self.__logger.debug(f"Rotctl odczyt pozycji: Az={az:.1f}°, El={el:.1f}°")
                        return az, el
                    else:
                        # Alternatywne parsowanie - wyciągnij liczby z całego tekstu
                        numbers = re.findall(r"[-+]?\d*\.?\d+", stdout)
                        if len(numbers) >= 2:
                            try:
                                az, el = float(numbers[0]), float(numbers[1])
                                self.__logger.debug(
                                    f"Rotctl odczyt pozycji (alt): Az={az:.1f}°, El={el:.1f}°"
                                )
                                return az, el
                            except ValueError:
                                pass

                        if attempt < retry_count:
                            self.__logger.warning(
                                f"Niepełna odpowiedź podczas próby {attempt + 1}: {stdout}, ponawiam..."
                            )
                            time.sleep(0.5)
                        else:
                            raise RuntimeError(
                                f"Niepełna odpowiedź pozycji rotctl: {stdout}"
                            )
                else:
                    if attempt < retry_count:
                        self.__logger.warning(
                            f"Błąd rotctl podczas próby {attempt + 1}: {stderr.strip()}, ponawiam..."
                        )
                        time.sleep(0.5)
                    else:
                        raise RuntimeError(
                            f"Błąd rotctl podczas odczytu pozycji: {stderr.strip()}"
                        )

            except subprocess.TimeoutExpired:
                proc.kill()
                if attempt < retry_count:
                    self.__logger.warning(
                        f"Timeout podczas odczytu pozycji, próba {attempt + 1}, ponawiam..."
                    )
                    time.sleep(0.5)
                else:
                    raise RuntimeError("Timeout podczas odczytu pozycji z rotctl po wszystkich próbach")
            except Exception as e:
                if attempt < retry_count:
                    self.__logger.warning(
                        f"Błąd podczas odczytu pozycji, próba {attempt + 1}: {e}, ponawiam..."
                    )
                    time.sleep(0.5)
                else:
                    raise RuntimeError(f"Błąd podczas odczytu pozycji z rotctl: {e}")
        return None

    def stop_rotor_move_rotctl(self, port: str, speed: int = DEFAULT_BAUDRATE,
                               model: str = DEFAULT_ROTCTL_MODEL) -> str:
        """
        Zatrzymuje ruch rotatora za pomocą rotctl.

        Args:
            port: Port szeregowy
            speed: Prędkość portu szeregowego
            model: Rotctl model

        Returns:
            Odpowiedź rotctl jako string

        Raises:
            RuntimeError: Jeśli komenda się nie powiodła
        """
        if not self.check_rotctl():
            raise RuntimeError("rotctl (Hamlib) nie jest dostępne w systemie")

        proc = subprocess.Popen(
            ["rotctl", "-m", model, "-r", port, "-s", str(speed), "-"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        try:
            stdout, stderr = proc.communicate(input="S\n", timeout=10)

            if proc.returncode != 0:
                raise RuntimeError(f"Błąd rotctl podczas zatrzymywania: {stderr.strip()}")

            self.__logger.info("Rotor zatrzymany za pomocą rotctl")
            return stdout.strip()

        except subprocess.TimeoutExpired:
            proc.kill()
            raise RuntimeError("Timeout podczas zatrzymywania rotora przez rotctl")
        except Exception as e:
            raise RuntimeError(f"Błąd podczas zatrzymywania rotora przez rotctl: {e}")


    def run_rotctl_command(self, command: list[str], model: str = DEFAULT_ROTCTL_MODEL,
            port: str = DEFAULT_SPID_PORT, baudrate: int = DEFAULT_BAUDRATE, timeout: int = 10
    ) -> subprocess.CompletedProcess:
        """
        Uruchamia komendę rotctl z standardowymi parametrami.

        Args:
            command: Lista argumentów komendy (bez rotctl, -m, -r, -s)
            model: Rotctl model
            port: Port SPID
            baudrate: Prędkość transmisji
            timeout: Timeout w sekundach

        Returns:
            Wynik subprocess.run
        """

        cmd = ["rotctl", "-m", model, "-r", port, "-s", str(baudrate), "-t", str(timeout)] + command
        self.__logger.debug(f"Wykonuję komendę rotctl: {' '.join(cmd)}")

        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 5, check=False)


    def test_spid_connection(self, port: str = DEFAULT_SPID_PORT, baudrate: int = DEFAULT_BAUDRATE, model:str = DEFAULT_ROTCTL_MODEL) -> bool:
        """
        Testuje połączenie ze SPID przez rotctl.

        Args:
            port: Port SPID
            baudrate: Prędkość transmisji

        Returns:
            True jeśli połączenie działa
        """
        try:
            result = self.run_rotctl_command(["get_pos"], port, baudrate, timeout=10)
            return result.returncode == 0
        except Exception as e:
            self.__logger.error(f"Błąd podczas testowania połączenia SPID: {e}")
            return False

    def get_best_spid_port(self, preferred_port: Optional[str] = None) -> str:
        """
        Zwraca najlepszy port dla kontrolera SPID.
        Sprawdza czy rotctl jest dostępne.
        """
        if not self.check_rotctl():
            raise RuntimeError("rotctl (Hamlib) nie jest dostępne w systemie")

        if preferred_port:
            self.__logger.info(f"Używam podanego portu: {preferred_port}")
            return preferred_port

        self.__logger.info(f"Używam domyślnego portu: {DEFAULT_SPID_PORT}")
        return DEFAULT_SPID_PORT

