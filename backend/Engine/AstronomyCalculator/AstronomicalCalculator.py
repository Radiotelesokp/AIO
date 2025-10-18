 from backend.Engine.AstronomyCalculator import ObserverLocation, AstronomicalObjectType, AstronomicalPosition
import math
import ephem
from datetime import datetime, timezone
from typing import Optional, Dict, Tuple


class AstronomicalCalculator:
    """Kalkulator pozycji astronomicznych"""

    def __init__(self, observer_location: ObserverLocation):
        self.observer_location = observer_location
        self.observer = ephem.Observer()
        self._setup_observer()

        # Słownik obiektów astronomicznych
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

        # Cache dla gwiazd
        self._star_cache: Dict[str, object] = {}

    def _setup_observer(self):
        """Konfiguruje obserwatora"""
        self.observer.lat = math.radians(self.observer_location.latitude)
        self.observer.lon = math.radians(self.observer_location.longitude)
        self.observer.elev = self.observer_location.elevation
        self.observer.pressure = 1013.25  # Ciśnienie atmosferyczne w hPa
        self.observer.temp = 15.0  # Temperatura w °C

    def get_position(
        self,
        object_type: AstronomicalObjectType,
        object_name: Optional[str] = None,
        star_coordinates: Optional[Tuple[float, float]] = None,
        observation_time: Optional[datetime] = None,
    ) -> AstronomicalPosition:
        """Oblicza pozycję obiektu astronomicznego"""
        if observation_time is None:
            observation_time = datetime.now(timezone.utc)

        # Ustawienie czasu obserwacji
        self.observer.date = observation_time.strftime("%Y/%m/%d %H:%M:%S")

        # Wybór obiektu
        if object_type == AstronomicalObjectType.STAR:
            if object_name:
                astronomical_object = self._get_star_by_name(object_name)
            elif star_coordinates:
                astronomical_object = self._create_star_from_coordinates(
                    star_coordinates[0], star_coordinates[1]
                )
            else:
                raise ValueError("Dla gwiazd wymagana jest nazwa lub współrzędne")

        elif object_type == AstronomicalObjectType.CUSTOM:
            if not star_coordinates:
                raise ValueError("Dla obiektu custom wymagane są współrzędne")
            astronomical_object = self._create_star_from_coordinates(
                star_coordinates[0], star_coordinates[1]
            )

        else:
            if object_type not in self._objects:
                raise ValueError(f"Nieobsługiwany typ obiektu: {object_type}")
            astronomical_object = self._objects[object_type]

        # Obliczenie pozycji
        astronomical_object.compute(self.observer)

        # Konwersja do stopni - PyEphem zwraca azymut w konwencji astronomicznej
        # (0° = północ, 90° = wschód) co jest zgodne z rotctl
        # Elewacja z PyEphem: 0° = horyzont, 90° = zenit (standardowa)
        azimuth = math.degrees(astronomical_object.az)
        elevation = math.degrees(astronomical_object.alt)

        # Dodatkowe informacje
        distance = (
            astronomical_object.earth_distance
            if hasattr(astronomical_object, "earth_distance")
            else 0.0
        )
        ra = math.degrees(astronomical_object.ra) / 15.0  # Konwersja do godzin
        dec = math.degrees(astronomical_object.dec)

        # Jasność pozorna (jeśli dostępna)
        magnitude = (
            astronomical_object.mag if hasattr(astronomical_object, "mag") else 0.0
        )

        return AstronomicalPosition(
            azimuth=azimuth,
            elevation=elevation,
            distance=distance,
            ra=ra,
            dec=dec,
            is_visible=elevation > 0,
            magnitude=magnitude,
        )

    def _get_star_by_name(self, star_name: str) -> object:
        """Pobiera gwiazdę po nazwie z cache lub tworzy nową"""
        if star_name in self._star_cache:
            return self._star_cache[star_name]

        # Próba znalezienia gwiazdy w katalogu
        try:
            star = ephem.star(star_name)
            self._star_cache[star_name] = star
            return star
        except Exception:
            raise ValueError(f"Nie znaleziono gwiazdy: {star_name}")

    @staticmethod
    def _create_star_from_coordinates(ra_hours: float, dec_degrees: float) -> object:
        """Tworzy obiekt gwiazdy ze współrzędnych"""
        star = ephem.FixedBody()
        star._ra = ephem.hours(ra_hours)
        star._dec = ephem.degrees(dec_degrees)
        star._epoch = ephem.J2000
        return star

    def get_sun_position(
        self, observation_time: Optional[datetime] = None
    ) -> AstronomicalPosition:
        """Skrócona metoda dla pozycji Słońca"""
        return self.get_position(
            AstronomicalObjectType.SUN, observation_time=observation_time
        )

    def get_moon_position(
        self, observation_time: Optional[datetime] = None
    ) -> AstronomicalPosition:
        """Skrócona metoda dla pozycji Księżyca"""
        return self.get_position(
            AstronomicalObjectType.MOON, observation_time=observation_time
        )

    def get_planet_position(
        self,
        planet: AstronomicalObjectType,
        observation_time: Optional[datetime] = None,
    ) -> AstronomicalPosition:
        """Skrócona metoda dla pozycji planet"""
        if planet not in [
            AstronomicalObjectType.MERCURY,
            AstronomicalObjectType.VENUS,
            AstronomicalObjectType.MARS,
            AstronomicalObjectType.JUPITER,
            AstronomicalObjectType.SATURN,
            AstronomicalObjectType.URANUS,
            AstronomicalObjectType.NEPTUNE,
        ]:
            raise ValueError(f"Nieprawidłowy typ planety: {planet}")

        return self.get_position(planet, observation_time=observation_time)

    def get_star_position(
        self, star_name: str, observation_time: Optional[datetime] = None
    ) -> AstronomicalPosition:
        """Skrócona metoda dla pozycji gwiazdy"""
        return self.get_position(
            AstronomicalObjectType.STAR,
            object_name=star_name,
            observation_time=observation_time,
        )

    def get_custom_position(
        self,
        ra_hours: float,
        dec_degrees: float,
        observation_time: Optional[datetime] = None,
    ) -> AstronomicalPosition:
        """Skrócona metoda dla pozycji obiektu o podanych współrzędnych"""
        return self.get_position(
            AstronomicalObjectType.CUSTOM,
            star_coordinates=(ra_hours, dec_degrees),
            observation_time=observation_time,
        )

    def calculate_rise_set_times(
        self,
        object_type: AstronomicalObjectType,
        object_name: Optional[str] = None,
        star_coordinates: Optional[Tuple[float, float]] = None,
        date: Optional[datetime] = None,
    ) -> Dict[str, Optional[datetime]]:
        """Oblicza czasy wschodu i zachodu obiektu"""
        if date is None:
            date = datetime.now(timezone.utc)

        self.observer.date = date.strftime("%Y/%m/%d")

        # Wybór obiektu
        if object_type == AstronomicalObjectType.STAR:
            if object_name:
                astronomical_object = self._get_star_by_name(object_name)
            elif star_coordinates:
                astronomical_object = self._create_star_from_coordinates(
                    star_coordinates[0], star_coordinates[1]
                )
            else:
                raise ValueError("Dla gwiazd wymagana jest nazwa lub współrzędne")
        else:
            astronomical_object = self._objects[object_type]

        try:
            rise_time = self.observer.next_rising(astronomical_object)
            set_time = self.observer.next_setting(astronomical_object)
            transit_time = self.observer.next_transit(astronomical_object)

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
        """Sprawdza, czy obiekt jest widoczny (nad horyzontem)"""
        position = self.get_position(
            object_type, object_name, star_coordinates, observation_time
        )
        return position.elevation >= min_elevation