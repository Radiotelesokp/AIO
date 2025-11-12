from .AstronomicalCalculator import AstronomicalCalculator
from .AstronomicalTracker import AstronomicalTracker
from .AstronomicalPosition import AstronomicalPosition
from .AstronomicalObjectTypeEnum import AstronomicalObjectType
from .ObserverLocation import ObserverLocation


__all__ = ["AstronomicalCalculator", "AstronomicalTracker", "AstronomicalPosition", "AstronomicalObjectType",
           "ObserverLocation", "BRIGHT_STARS"]
__author__ = "Aleks Czarnecki"
__version__ = "0.1.0"
__editor__ = "Wiktoria Dębowska"

# Jasne gwiazdy do testów
BRIGHT_STARS = {
    "sirius": "Sirius",
    "vega": "Vega",
    "arcturus": "Arcturus",
    "capella": "Capella",
    "rigel": "Rigel",
    "procyon": "Procyon",
    "betelgeuse": "Betelgeuse",
    "aldebaran": "Aldebaran",
    "spica": "Spica",
    "antares": "Antares",
    "pollux": "Pollux",
    "fomalhaut": "Fomalhaut",
    "deneb": "Deneb",
    "regulus": "Regulus",
}