class AntennaError(Exception):
    """Base exception for antenna errors"""


class CommunicationError(AntennaError):
    """Communication error with the controller"""


class PositionError(AntennaError):
    """Antenna positioning error"""


class SafetyError(AntennaError):
    """Safety error – limits exceeded"""