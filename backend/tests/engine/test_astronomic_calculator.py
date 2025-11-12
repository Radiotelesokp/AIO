# Przykład użycia
from datetime import datetime, timezone

from Engine.AstronomyCalculator.AstronomicalCalculator import AstronomicalCalculator
from Engine.AstronomyCalculator.AstronomicalTracker import AstronomicalTracker
from Engine.AstronomyCalculator.AstronomicalObjectTypeEnum import AstronomicalObjectType
from Engine.ObservatoryConfig import get_observer_location
from LanguageHelper import LanguageHelper

languageHelper = LanguageHelper("pl", "en")

def test_astronomic_calculator():
    observer_location = get_observer_location("polanka", languageHelper)
    calculator = AstronomicalCalculator(observer_location, languageHelper)
    tracker = AstronomicalTracker(calculator)

    print(f"Obserwator: {observer_location.name}")
    print(f"Współrzędne: {observer_location.latitude:.4f}°N, {observer_location.longitude:.4f}°E")
    print(f"Wysokość: {observer_location.elevation}m n.p.m.\n")

    # Test pozycji różnych obiektów
    objects_to_test = [
        (AstronomicalObjectType.SUN, "Słońce"),
        (AstronomicalObjectType.MOON, "Księżyc"),
        (AstronomicalObjectType.MARS, "Mars"),
        (AstronomicalObjectType.JUPITER, "Jowisz"),
        (AstronomicalObjectType.VENUS, "Wenus"),
    ]

    current_time = datetime.now(timezone.utc)
    print(f"Czas obserwacji: {current_time.strftime('%d/%m/%Y %H:%M:%S UTC+0')}\n")

    for obj_type, obj_name in objects_to_test:
        try:
            position = calculator.get_position(obj_type)
            antenna_pos = position.to_antenna_position()

            print(f"{obj_name}:")
            print(f"  Azymut: {position.azimuth:.2f}° (rotctl)")
            print(f"  Elewacja: {position.elevation:.2f}° (standardowa)")
            print(f"  Widoczny: {'Tak' if position.is_visible else 'Nie'}")
            print(f"  Jasność: {position.magnitude:.1f}m")
            if antenna_pos:
                print(f"Pozycja SPID: Az={antenna_pos.azimuth:.2f}°, El={antenna_pos.elevation:.2f}° (90°=horyzont)")
            print()

        except Exception as e:
            print(f"Błąd dla {obj_name}: {e}\n")

    # Test śledzenia Słońca
    print("Test funkcji śledzenia Słońca:")
    sun_tracker = tracker.track_sun()