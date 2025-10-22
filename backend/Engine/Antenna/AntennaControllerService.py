import logging
import time
import subprocess
import re
from typing import Optional, Any

from Engine.Antenna.Constants import DEFAULT_ROTCTL_MODEL, DEFAULT_TIMEOUT, DEFAULT_BAUDRATE, DEFAULT_SPID_PORT
from Engine.Antenna.AntennaControllerHelper import *
from LanguageHelper import LanguageHelper


class AntennaControllerService:
    __logger = logging.getLogger(__name__)

    def __init__(self, languageHelper: LanguageHelper):
        self.__languageHelper = languageHelper
        self._ = self.__languageHelper.getTranslatedMessage("Antenna")

    def check_rotctl(self) -> bool:
        """ Check availability of rotctl in the operating system. """
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
        Sets the SPID rotator position using rotctl (Hamlib).

        Args:
            port: Serial port (e.g. '/dev/tty.usbserial-A10PDNT7')
            az: Azimuth in degrees (0-360)
            el: Elevation in degrees (-90 to +90)
            speed: Serial port speed
            retry_count: Number of retry attempts on failure
            model: Rotctl model

        Returns:
            rotctl response as a string

        Raises:
            RuntimeError: If the command fails after all attempts
        """
        if not self.check_rotctl():
            raise RuntimeError(f"{self._('rotctl.motor.hamlib.is.unavailable.error')}")

        command = f"P {az % 360:.1f} {el:.1f}\n"
        normalized_az = az % 360

        if AntennaLimits.max_elevation < abs(el):  # check limits
            raise SafetyError(f"{self._("rotctl.motor.elevation.out.of.range.error").format(el=el)}")
        self.__logger.info(f"Rotctl: Sending position command - Az={normalized_az:.1f}°, El={el:.1f}°")

        for attempt in range(retry_count + 1):
            proc = subprocess.Popen(["rotctl", "-m", model, "-r", port, "-s", str(speed), "-"],
                                    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            try:
                stdout, stderr = proc.communicate(input=command, timeout=15)

                if proc.returncode == 0:
                    self.__logger.debug(f"Rotctl set position Az={normalized_az:.1f}°, El={el:.1f}° - response: {stdout.strip()}")
                    return stdout.strip()
                else:
                    error_msg = stderr.strip() if stderr.strip() else stdout.strip()
                    if attempt < retry_count:
                        self.__logger.warning(f"Attempt {attempt + 1} failed, code: {proc.returncode}, error: '{error_msg}', retrying...")
                        time.sleep(1)
                    else:
                        raise CommunicationError(f"{self._('rotctl.motor.setting.position.error').format(
                            normalized_az=normalized_az, el=el, code =proc.returncode, error_msg=error_msg)}")

            except subprocess.TimeoutExpired:
                proc.kill()
                if attempt < retry_count:
                    self.__logger.warning(f"Timeout during attempt {attempt + 1}, retrying...")
                    time.sleep(1)
                else:
                    raise TimeoutError(f"{self._('rotctl.motor.timeout.set.after.all.attempts')}")

            except Exception as e:
                if attempt < retry_count:
                    self.__logger.warning(f"Error during attempt {attempt + 1}: {e}, retrying...")
                    time.sleep(1)
                else:
                    raise CommunicationError(f"{self._('rotctl.motor.communication.error')} {e}")
        return ""

    def read_position_rotctl(self, port: str, speed: int = DEFAULT_BAUDRATE, retry_count: int = 2,
                             model: str = DEFAULT_ROTCTL_MODEL) -> tuple[Any, Any] | tuple[float, float] | None:
        """
        Reads the current SPID rotator position using rotctl.

        Args:
            port: Serial port
            speed: Serial port speed
            retry_count: Number of retry attempts on failure
            model: Rotctl model

        Returns:
            Tuple (azimuth, elevation) in degrees

        Raises:
            RuntimeError: If the read fails after all attempts
        """
        if not self.check_rotctl():
            raise RuntimeError(f"{self._("rotctl.motor.hamlib.is.unavailable.error")}")

        for attempt in range(retry_count + 1):
            proc = subprocess.Popen(
                ["rotctl", "-m", model, "-r", port, "-s", str(speed), "-"],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            try:
                stdout, stderr = proc.communicate(input="p\n", timeout=15)

                if proc.returncode == 0:
                    lines = stdout.strip().split("\n")  # Parse rotctl response
                    values = []

                    for line in lines:
                        line = line.strip()
                        if line and not line.startswith("p "):
                            try:
                                values.append(float(line))
                            except ValueError:
                                if line.startswith("p "):  # Check if line contains value after "p "
                                    try:
                                        values.append(float(line[2:]))
                                    except ValueError:
                                        continue

                    if len(values) >= 2:
                        az, el = values[0], values[1]
                        self.__logger.debug(f"Rotctl read position: Az={az:.1f}°, El={el:.1f}°")
                        return az, el
                    else:
                        numbers = re.findall(r"[-+]?\d*\.?\d+", stdout)  # Alternative parsing - extract all numbers
                        if len(numbers) >= 2:
                            try:
                                az, el = float(numbers[0]), float(numbers[1])
                                self.__logger.debug(f"Rotctl read position (alt): Az={az:.1f}°, El={el:.1f}°")
                                return az, el
                            except ValueError:
                                pass

                        if attempt < retry_count:
                            self.__logger.warning(f"Incomplete response during attempt {attempt + 1}: {stdout}, retrying...")
                            time.sleep(0.5)
                        else:
                            raise CommunicationError(f"{self._('rotctl.motor.incomplete.position.response')} {stdout}")
                else:
                    if attempt < retry_count:
                        self.__logger.warning(f"Rotctl error during attempt {attempt + 1}: {stderr.strip()}, retrying...")
                        time.sleep(0.5)
                    else:
                        raise AntennaError(f"{self._('rotctl.motor.reading.position.error')} {stderr.strip()}")

            except subprocess.TimeoutExpired:
                proc.kill()
                if attempt < retry_count:
                    self.__logger.warning(f"Timeout while reading position, attempt {attempt + 1}, retrying...")
                    time.sleep(0.5)
                else:
                    raise TimeoutError("rotctl.motor.timeout.reading.after.all.attempts")
            except Exception as e:
                if attempt < retry_count:
                    self.__logger.warning(f"Error while reading position, attempt {attempt + 1}: {e}, retrying...")
                    time.sleep(0.5)
                else:
                    raise AntennaError(f"{self._('rotctl.motor.reading.position.error')} {e}")
        return None

    def stop_rotor_move_rotctl(self, port: str, speed: int = DEFAULT_BAUDRATE,
                               model: str = DEFAULT_ROTCTL_MODEL) -> str:
        """ Stops the rotator movement using rotctl.
        Args:
            port: Serial port
            speed: Serial port speed
            model: Rotctl model

        Returns:
            rotctl response as a string

        Raises:
            RuntimeError: If the command fails
        """
        if not self.check_rotctl():
            raise RuntimeError(f"{self._("rotctl.motor.hamlib.is.unavailable.error")}")

        proc = subprocess.Popen(["rotctl", "-m", model, "-r", port, "-s", str(speed), "-"],
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        try:
            stdout, stderr = proc.communicate(input="S\n", timeout=10)

            if proc.returncode != 0:
                raise CommunicationError(f"{self._("rotctl.motor.cannot.stop.antena.proc.error")} {stderr.strip()}")

            self.__logger.info("Rotor stopped using rotctl")
            return stdout.strip()

        except subprocess.TimeoutExpired:
            proc.kill()
            raise TimeoutError({self._("rotctl.motor.cannot.stop.antena.timeout.error")})
        except Exception as e:
            raise AntennaError(f"{self._("rotctl.motor.cannot.stop.antena.error")}: {e}")

    def run_rotctl_command(self, command: list[str], model: str = DEFAULT_ROTCTL_MODEL,
                           port: str = DEFAULT_SPID_PORT, baudrate: int = DEFAULT_BAUDRATE, timeout: int = 10
                           ) -> subprocess.CompletedProcess:
        """ Executes a rotctl command with standard parameters.
        Args:
            command: List of command arguments (without rotctl, -m, -r, -s)
            model: Rotctl model
            port: SPID port
            baudrate: Transmission speed
            timeout: Timeout in seconds

        Returns:
            subprocess.run result
        """

        cmd = ["rotctl", "-m", model, "-r", port, "-s", str(baudrate), "-t", str(timeout)] + command
        self.__logger.debug(f"Executing rotctl command: {' '.join(cmd)}")

        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 5, check=False)

    def test_spid_connection(self, port: str = DEFAULT_SPID_PORT, baudrate: int = DEFAULT_BAUDRATE) -> bool:
        """ Tests the connection with SPID via rotctl.
        Args:
            port: SPID port
            baudrate: Transmission speed

        Returns:
            True if the connection works
        """
        try:
            result = self.run_rotctl_command(["get_pos"], port=port, baudrate=baudrate, timeout=10)
            return result.returncode == 0
        except Exception as e:
            self.__logger.error(f"Error while testing SPID connection: {e}")
            return False

    def get_best_spid_port(self, preferred_port: Optional[str] = None) -> str:
        """ Returns the best port for the SPID controller. Checks if rotctl is available. """
        if not self.check_rotctl():
            raise RuntimeError(f"{self._("rotctl.motor.hamlib.is.unavailable.error")}")

        if preferred_port:
            self.__logger.info(f"Using provided port: {preferred_port}")
            return preferred_port

        self.__logger.info(f"Using default port: {DEFAULT_SPID_PORT}")
        return DEFAULT_SPID_PORT