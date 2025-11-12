import time
import logging
from Engine.Antenna import Position, AntennaControllerFactory, DEFAULT_BAUDRATE
from Engine.Antenna.AntennaControllerHelper import AntennaState
from Engine.Antenna.Motor import MotorConfig
from LanguageHelper import LanguageHelper

languageHelper = LanguageHelper("pl", "en")

# Przykład użycia
if __name__ == "__main__":
    logger = logging.getLogger(__name__)

    def status_callback(position: Position, state: AntennaState):
        """Callback wywoływany przy zmianie stanu"""
        print(
            f"Status: {state.value}, Pozycja: Az={position.azimuth:.2f}°, El={position.elevation:.2f}°"
        )

    # Konfiguracja
    motor_config = MotorConfig(
        steps_per_revolution=200,
        microsteps=16,
    )

    # Limity zostaną wczytane z pliku kalibracji automatycznie

    # Przykład użycia z SPID
    try:
        controller = AntennaControllerFactory.create_spid_controller(
            port="/dev/tty.usbserial-A10PDNT7",  # Twój port
            baudrate=DEFAULT_BAUDRATE,
            motor_config=motor_config,
        )
        controller.initialize()  # Próbuj zainicjalizować
        print("Utworzono kontroler SPID")
    except Exception as e:
        # Fallback na symulator jeśli nie można połączyć z prawdziwym urządzeniem
        print(f"Nie można połączyć z SPID ({e}), przełączam na symulator")
        controller = AntennaControllerFactory.create_simulator_controller(
            simulation_speed=2000.0, motor_config=motor_config, languageHelper= languageHelper
        )
        print("Utworzono symulator (brak dostępu do prawdziwego urządzenia)")

    # Przypisanie callbacku
    controller.update_callback = status_callback

    try:
        # Inicjalizacja (jeśli jeszcze nie została wykonana)
        if not hasattr(controller, "_initialized") or not controller._initialized:
            controller.initialize()
            controller._initialized = True
        print("System zainicjalizowany")

        # Test ruchu
        target_positions = [
            Position(20.0, 0.0),
            Position(45.0, 30.0),
            Position(90.0, 45.0),
            Position(0.0, 0.0),  # powrót do pozycji domowej
        ]

        for pos in target_positions:
            print(f"\nRuch do pozycji: Az={pos.azimuth}°, El={pos.elevation}°")
            controller.move_to(pos)

            # Czekaj na zakończenie ruchu
            while controller.state == AntennaState.MOVING:
                time.sleep(0.5)

            print(f"Osiągnięto pozycję: {controller.current_position}")
            time.sleep(1)

        # Test komendy STOP
        print("\nTest komendy STOP...")
        controller.move_to(Position(180.0, 45.0))
        time.sleep(3)  # Pozwól na rozpoczęcie ruchu
        controller.stop()

        # Wyświetl status końcowy
        status = controller.get_status()
        print(f"\nStatus końcowy: {status}")

    except Exception as e:
        print(f"Błąd: {e}")
        logger.error(f"Błąd główny: {e}")

    finally:
        controller.shutdown()
        print("System wyłączony")