from .ObserverLocation import ObserverLocation
from .AstronomicalObjectTypeEnum import AstronomicalObjectType
from .AstronomicalPosition import AstronomicalPosition
import math
import ephem
from datetime import datetime, timezone
from typing import Optional, Dict, Tuple


class AstronomicalCalculator:
    """Astronomical position calculator"""

    def __init__(self, observer_location: ObserverLocation, languageHelper):
        self.__observer_location = observer_location
        self.__observer = ephem.Observer()
        self.__setup_observer()
        self.__languageHelper = languageHelper
        self._ = self.__languageHelper.getTranslatedMessage("AstronomyCalculator")

        # Dictionary of astronomical objects
        # pylint: disable=no-member  # ephem objects exist at runtime
        self._objects = {
            AstronomicalObjectType.SUN: ephem.Sun(),
            AstronomicalObjectType.MOON: ephem.Moon(),
            AstronomicalObjectType.MERCURY: ephem.Mercury(),
            AstronomicalObjectType.VENUS: ephem.Venus(),
            AstronomicalObjectType.MARS: ephem.Mars(),
            AstronomicalObjectType.JUPITER: ephem.Jupiter(),
            AstronomicalObjectType.SATURN: ephem.Saturn(),
            AstronomicalObjectType.URANUS: ephem.Uranus(),
            AstronomicalObjectType.NEPTUNE: ephem.Neptune(),
        }

        # Cache for stars
        self._star_cache: Dict[str, object] = {}

    def __setup_observer(self):
        """Configures the observer"""
        self.__observer.lat = math.radians(self.__observer_location.latitude)
        self.__observer.lon = math.radians(self.__observer_location.longitude)
        self.__observer.elev = self.__observer_location.elevation
        self.__observer.pressure = 1013.25  # Atmospheric pressure in hPa
        self.__observer.temp = 15.0  # Temperature in °C

    def get_position(
        self,
        object_type: AstronomicalObjectType,
        object_name: Optional[str] = None,
        star_coordinates: Optional[Tuple[float, float]] = None,
        observation_time: Optional[datetime] = None,
    ) -> AstronomicalPosition:
        """Calculates the position of an astronomical object"""
        if observation_time is None:
            observation_time = datetime.now(timezone.utc)

        # Set observation time
        self.__observer.date = observation_time.strftime("%Y/%m/%d %H:%M:%S")

        # Select object
        if object_type == AstronomicalObjectType.STAR:
            if object_name:
                astronomical_object = self._get_star_by_name(object_name)
            elif star_coordinates:
                astronomical_object = self._create_star_from_coordinates(
                    star_coordinates[0], star_coordinates[1]
                )
            else:
                raise ValueError(f"{self._('astronomical.calculator.required.name.star')}")

        elif object_type == AstronomicalObjectType.CUSTOM:
            if not star_coordinates:
                raise ValueError(f"{self._('astronomical.calculator.required.name.custom')}")
            astronomical_object = self._create_star_from_coordinates(
                star_coordinates[0], star_coordinates[1]
            )

        else:
            if object_type not in self._objects:
                raise ValueError(f"{self._('astronomical.calculator.unsupported.object.type')} {object_type}")
            astronomical_object = self._objects[object_type]

        # Calculate position
        astronomical_object.compute(self.__observer)

        # Convert to degrees - PyEphem returns azimuth in astronomical convention
        # (0° = north, 90° = east), which is consistent with rotctl
        # Elevation from PyEphem: 0° = horizon, 90° = zenith (standard)
        azimuth = math.degrees(astronomical_object.az)
        elevation = math.degrees(astronomical_object.alt)

        # Additional information
        distance = (
            astronomical_object.earth_distance
            if hasattr(astronomical_object, "earth_distance")
            else 0.0
        )
        ra = math.degrees(astronomical_object.ra) / 15.0  # Convert to hours
        dec = math.degrees(astronomical_object.dec)

        # Apparent magnitude (if available)
        magnitude = astronomical_object.mag if hasattr(astronomical_object, "mag") else 0.0

        return AstronomicalPosition(azimuth=azimuth, elevation=elevation, distance=distance, ra=ra, dec=dec,
                                    is_visible=elevation > 0, magnitude=magnitude, languageHelper=self.__languageHelper)

    def _get_star_by_name(self, star_name: str) -> object:
        """Fetches a star by name from cache or creates a new one"""
        if star_name in self._star_cache:
            return self._star_cache[star_name]

        # Attempt to find the star in the catalog
        try:
            star = ephem.star(star_name)
            self._star_cache[star_name] = star
            return star
        except Exception:
            raise ValueError(f"{self._('astronomical.calculator.star.not.found')} {star_name}")

    @staticmethod
    def _create_star_from_coordinates(ra_hours: float, dec_degrees: float) -> object:
        """Creates a star object from coordinates"""
        star = ephem.FixedBody()
        star._ra = ephem.hours(ra_hours)
        star._dec = ephem.degrees(dec_degrees)
        star._epoch = ephem.J2000
        return star

    def get_sun_position(
        self, observation_time: Optional[datetime] = None
    ) -> AstronomicalPosition:
        """Shortcut method for Sun position"""
        return self.get_position(AstronomicalObjectType.SUN, observation_time=observation_time)

    def get_moon_position(
        self, observation_time: Optional[datetime] = None
    ) -> AstronomicalPosition:
        """Shortcut method for Moon position"""
        return self.get_position(AstronomicalObjectType.MOON, observation_time=observation_time)

    def get_planet_position(self, planet: AstronomicalObjectType, observation_time: Optional[datetime] = None) -> AstronomicalPosition:
        """Shortcut method for planet positions"""
        if planet not in [
            AstronomicalObjectType.MERCURY,
            AstronomicalObjectType.VENUS,
            AstronomicalObjectType.MARS,
            AstronomicalObjectType.JUPITER,
            AstronomicalObjectType.SATURN,
            AstronomicalObjectType.URANUS,
            AstronomicalObjectType.NEPTUNE,
        ]:
            raise ValueError(f"{self._('astronomical.calculator.bad.planet.name')} {planet}")

        return self.get_position(planet, observation_time=observation_time)

    def get_star_position(
        self, star_name: str, observation_time: Optional[datetime] = None
    ) -> AstronomicalPosition:
        """Shortcut method for star position"""
        return self.get_position(AstronomicalObjectType.STAR, object_name=star_name, observation_time=observation_time)

    def get_custom_position(self, ra_hours: float, dec_degrees: float, observation_time: Optional[datetime] = None) -> AstronomicalPosition:
        """Shortcut method for position of a custom object with given coordinates"""
        return self.get_position(AstronomicalObjectType.CUSTOM, star_coordinates=(ra_hours, dec_degrees), observation_time=observation_time)

    def calculate_rise_set_times(
        self,
        object_type: AstronomicalObjectType,
        object_name: Optional[str] = None,
        star_coordinates: Optional[Tuple[float, float]] = None,
        date: Optional[datetime] = None,
    ) -> Dict[str, Optional[datetime]]:
        """Calculates rise and set times for an object"""
        if date is None:
            date = datetime.now(timezone.utc)

        self.__observer.date = date.strftime("%Y/%m/%d")

        # Select object
        if object_type == AstronomicalObjectType.STAR:
            if object_name:
                astronomical_object = self._get_star_by_name(object_name)
            elif star_coordinates:
                astronomical_object = self._create_star_from_coordinates(
                    star_coordinates[0], star_coordinates[1]
                )
            else:
                raise ValueError(f"{self._('astronomical.calculator.required.name.star')}")
        else:
            astronomical_object = self._objects[object_type]

        try:
            rise_time = self.__observer.next_rising(astronomical_object)
            set_time = self.__observer.next_setting(astronomical_object)
            transit_time = self.__observer.next_transit(astronomical_object)

            return {
                "rise": ephem.localtime(rise_time),
                "set": ephem.localtime(set_time),
                "transit": ephem.localtime(transit_time),
            }
        except Exception:
            return {"rise": None, "set": None, "transit": None}

    def is_object_visible(
        self,
        object_type: AstronomicalObjectType,
        object_name: Optional[str] = None,
        star_coordinates: Optional[Tuple[float, float]] = None,
        min_elevation: float = 0.0,
        observation_time: Optional[datetime] = None,
    ) -> bool:
        """Checks whether the object is visible (above the horizon)"""
        position = self.get_position(
            object_type, object_name, star_coordinates, observation_time
        )
        return position.elevation >= min_elevation