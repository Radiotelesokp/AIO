from enum import Enum


class AstronomicalObjectType(Enum):
    """Typy obiektów astronomicznych"""

    SUN = "sun"
    MOON = "moon"
    MERCURY = "mercury"
    VENUS = "venus"
    MARS = "mars"
    JUPITER = "jupiter"
    SATURN = "saturn"
    URANUS = "uranus"
    NEPTUNE = "neptune"
    STAR = "star"
    CUSTOM = "custom"