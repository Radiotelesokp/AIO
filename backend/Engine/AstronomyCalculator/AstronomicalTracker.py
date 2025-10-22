import logging
from typing import Optional, Tuple

from ..Antenna.Position.Position import Position
from .AstronomicalObjectTypeEnum import AstronomicalObjectType
from .AstronomicalCalculator import AstronomicalCalculator


class AstronomicalTracker:
    """Class for tracking astronomical objects"""
    __logger = logging.getLogger(__name__)

    def __init__(self, calculator: AstronomicalCalculator):
        self.calculator = calculator
        self.tracking_active = False
        self.current_target = None
        self.tracking_precision = 0.1  # Degrees

    def create_position_function(
            self,
            object_type: AstronomicalObjectType,
            object_name: Optional[str] = None,
            star_coordinates: Optional[Tuple[float, float]] = None
    ):
        """
        Creates a position function to be used with the antenna controller
        """

        def get_position() -> Optional[Position]:
            try:
                # Get the current astronomical position
                ast_position = self.calculator.get_position(
                    object_type, object_name, star_coordinates
                )

                # Check visibility
                if not ast_position.is_visible:
                    return None

                # Convert to antenna position
                antenna_position = ast_position.to_antenna_position()
                return antenna_position

            except Exception as e:
                self.__logger.error(f"Error calculating position: {e}")
                return None

        return get_position

    def track_sun(self):
        """Returns a function for tracking the Sun"""
        return self.create_position_function(AstronomicalObjectType.SUN)

    def track_moon(self):
        """Returns a function for tracking the Moon"""
        return self.create_position_function(AstronomicalObjectType.MOON)

    def track_planet(self, planet: AstronomicalObjectType):
        """Returns a function for tracking a planet"""
        return self.create_position_function(planet)

    def track_star(self, star_name: str):
        """Returns a function for tracking a star"""
        return self.create_position_function(AstronomicalObjectType.STAR, object_name=star_name)

    def track_coordinates(self, ra_hours: float, dec_degrees: float):
        """Returns a function for tracking by coordinates"""
        return self.create_position_function(AstronomicalObjectType.CUSTOM, star_coordinates=(ra_hours, dec_degrees))