from backend.Engine.Antenna.AntennaControllerFactory import AntennaControllerFactory
from backend.Engine.Antenna.AntennaController import AntennaController
from backend.Engine.Antenna.AntennaControlerSerivce import AntennaControllerService
from backend.Engine.Antenna.Position import Position

# Domyślny port szeregowy dla kontrolera SPID
DEFAULT_SPID_PORT = "/dev/tty.usbserial-A10PDNT7"

# Wspólne stałe konfiguracyjne
DEFAULT_BAUDRATE = 115200
DEFAULT_ROTCTL_MODEL = "903"
DEFAULT_TIMEOUT = 5

# Domyślna ścieżka do pliku konfiguracji kalibracji
DEFAULT_CALIBRATION_FILE = "resource/antenna_calibration.json"


__all__ = ["AntennaControllerService", "AntennaController", "AntennaControllerFactory", "Position",
           "DEFAULT_SPID_PORT", "DEFAULT_BAUDRATE", "DEFAULT_TIMEOUT", "DEFAULT_ROTCTL_MODEL",
           "DEFAULT_CALIBRATION_FILE"]
__author__ = "Aleks Czarnecki"
__version__ = "0.1.0"
__editor__ = "Wiktoria Dębowska"