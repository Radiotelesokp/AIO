from typing import Optional, Tuple
from backend.Engine.antenna_controller import Position
from backend.Engine.AstronomyCalculator import AstronomicalObjectType, AstronomicalCalculator


class AstronomicalTracker:
    """Klasa do śledzenia obiektów astronomicznych"""

    def __init__(self, calculator: AstronomicalCalculator):
        self.calculator = calculator
        self.tracking_active = False
        self.current_target = None
        self.tracking_precision = 0.1  # Stopnie

    def create_position_function(
        self,
        object_type: AstronomicalObjectType,
        object_name: Optional[str] = None,
        star_coordinates: Optional[Tuple[float, float]] = None,
    ):
        """
        Tworzy funkcję pozycji do użycia z kontrolerem anteny
        """

        def get_position() -> Optional[Position]:
            try:
                # Pobierz aktualną pozycję astronomiczną
                ast_position = self.calculator.get_position(
                    object_type, object_name, star_coordinates
                )

                # Sprawdź widoczność
                if not ast_position.is_visible:
                    return None

                # Konwertuj na pozycję anteny
                antenna_position = ast_position.to_antenna_position()
                return antenna_position

            except Exception as e:
                print(f"Błąd obliczania pozycji: {e}")
                return None

        return get_position

    def track_sun(self):
        """Zwraca funkcję śledzenia Słońca"""
        return self.create_position_function(AstronomicalObjectType.SUN)

    def track_moon(self):
        """Zwraca funkcję śledzenia Księżyca"""
        return self.create_position_function(AstronomicalObjectType.MOON)

    def track_planet(self, planet: AstronomicalObjectType):
        """Zwraca funkcję śledzenia planety"""
        return self.create_position_function(planet)

    def track_star(self, star_name: str):
        """Zwraca funkcję śledzenia gwiazdy"""
        return self.create_position_function(
            AstronomicalObjectType.STAR,
            object_name=star_name,
        )

    def track_coordinates(
        self, ra_hours: float, dec_degrees: float):
        """Zwraca funkcję śledzenia współrzędnych"""
        return self.create_position_function(
            AstronomicalObjectType.CUSTOM,
            star_coordinates=(ra_hours, dec_degrees),
        )