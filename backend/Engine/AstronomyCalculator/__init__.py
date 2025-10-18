from backend.Engine.AstronomyCalculator.AstronomicalCalculator import AstronomicalCalculator
from backend.Engine.AstronomyCalculator.AstronomicalTracker import AstronomicalTracker
from backend.Engine.AstronomyCalculator.AstronomicalPosition import AstronomicalPosition
from backend.Engine.AstronomyCalculator.AstronomicalObjectTypeEnum import AstronomicalObjectType
from backend.Engine.AstronomyCalculator.ObserverLocation import ObserverLocation


__all__ = ["AstronomicalCalculator", "AstronomicalTracker", "AstronomicalPosition", "AstronomicalObjectType", "ObserverLocation"]
__author__ = "Aleks Czarnecki"
__version__ = "0.1.0"
__editor__ = "Wiktoria Dębowska"

# Predefiniowane lokalizacje obserwatoriów
OBSERVATORIES = {
    "poznan": ObserverLocation(52.40030228321106, 16.955077591791788, 60, "Poznań Polanka")
}

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