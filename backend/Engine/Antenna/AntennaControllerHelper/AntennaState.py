from enum import Enum


class AntennaState(Enum):
    """Stany anteny"""

    IDLE = "idle"
    MOVING = "moving"
    ERROR = "error"
    STOPPED = "stopped"
    CALIBRATING = "calibrating"