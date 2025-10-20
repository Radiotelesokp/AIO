from enum import Enum


class AntennaState(Enum):
    """Antenna states"""

    IDLE = "idle"
    MOVING = "moving"
    ERROR = "error"
    STOPPED = "stopped"
    CALIBRATING = "calibrating"