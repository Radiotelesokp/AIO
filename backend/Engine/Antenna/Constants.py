import os

# Domyślny port szeregowy dla kontrolera SPID
DEFAULT_SPID_PORT = "/dev/tty.usbserial-A10PDNT7"

# Wspólne stałe konfiguracyjne
DEFAULT_BAUDRATE = 115200
DEFAULT_ROTCTL_MODEL = "903"
DEFAULT_TIMEOUT = 5

BACKEND_FILES = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENGINE_RESOURCES_DIR = os.path.join(BACKEND_FILES,"resource")
# Domyślna ścieżka do pliku konfiguracji kalibracji
DEFAULT_CALIBRATION_FILE = os.path.join(ENGINE_RESOURCES_DIR,"antenna_calibration.json")