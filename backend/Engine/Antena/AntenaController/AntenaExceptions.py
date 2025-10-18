from enum import Enum

class AntennaError(Exception):
    """Podstawowy wyjątek dla błędów anteny"""


class CommunicationError(AntennaError):
    """Błąd komunikacji z sterownikiem"""


class PositionError(AntennaError):
    """Błąd pozycjonowania anteny"""


class SafetyError(AntennaError):
    """Błąd bezpieczeństwa - przekrocenie limitów"""