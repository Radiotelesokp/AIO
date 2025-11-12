#!/usr/bin/env python3
"""
Program do automatycznej kalibracji offsetu anteny poprzez spiralny skan wokół pozycji Słońca.

Wykorzystuje istniejącą infrastrukturę projektu:
- AntennaControllerFactory do tworzenia kontrolera
- AstronomicalCalculator do wyliczania pozycji Słońca
- PositionCalibration do zarządzania kalibracją
- Integracja z SDR do pomiaru mocy sygnału (opcjonalnie)

Algorytm:
1. Pobiera teoretyczną pozycję Słońca
2. Wykonuje spiralny skan wokół tej pozycji
3. Mierzy moc sygnału w każdym punkcie (SDR lub symulacja)
4. Znajduje punkt z maksymalną mocą
5. Oblicza różnicę (offset) między pozycją teoretyczną a zmierzoną
6. Zapisuje offset używając PositionCalibration.save_to_file()
"""

import sys
import time
import json
import logging
from datetime import datetime
from pathlib import Path
import math
import os

# Dodaj ścieżkę do modułów projektu
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from Engine.AstronomyCalculator import (
    AstronomicalCalculator,
    AstronomicalObjectType,
    ObserverLocation
)
from Engine.Antenna import AntennaControllerFactory
from Engine.Antenna.AntennaControllerHelper import AntennaState
from Engine.Antenna.Position import Position, PositionCalibration
from Engine.Antenna.Motor import MotorConfig
from Engine.ObservatoryConfig import OBSERVATORIES, get_observer_location
from backend.LanguageHelper import LanguageHelper

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SpiralSunCalibration:
    """Klasa do przeprowadzania spiralnej kalibracji anteny na Słońcu."""
    
    def __init__(self, antenna_controller, observer_location: ObserverLocation, 
                 use_sdr=False, sdr_service=None):
        """
        Args:
            antenna_controller: Kontroler anteny z AntennaControllerFactory
            observer_location: Lokalizacja obserwatora
            use_sdr: Czy używać SDR do pomiaru mocy sygnału
            sdr_service: Serwis SDR (jeśli use_sdr=True)
        """
        self.antenna = antenna_controller
        self.observer = observer_location
        self.astro_calc = AstronomicalCalculator(observer_location)
        self.use_sdr = use_sdr
        self.sdr = sdr_service
        
        # Parametry spirali
        self.spiral_step = 0.5  # Krok spirali w stopniach
        self.max_radius = 10.0  # Maksymalny promień spirali w stopniach
        self.measurement_time = 2.0  # Czas pomiaru w sekundach na każdy punkt
        
        # Wyniki
        self.measurements = []
        self.best_position = None
        self.best_signal = -999.0
        
    def get_sun_position(self):
        """Pobiera aktualną teoretyczną pozycję Słońca."""
        sun_pos = self.astro_calc.calculate_object_position(AstronomicalObjectType.SUN)
        logger.info(f"Teoretyczna pozycja Słońca: Az={sun_pos.azimuth:.2f}°, El={sun_pos.elevation:.2f}°")
        return sun_pos
    
    def generate_spiral_points(self, center_az, center_el):
        """
        Generuje punkty spirali Archimedesa wokół centrum.
        
        Args:
            center_az: Azymut centrum (stopnie)
            center_el: Elewacja centrum (stopnie)
            
        Returns:
            Lista krotek (azymut, elewacja)
        """
        points = [(center_az, center_el)]  # Zaczynamy od centrum
        
        angle = 0
        radius = 0
        
        while radius <= self.max_radius:
            # Spirala Archimedesa: r = a * θ
            angle += self.spiral_step * 10  # Kąt w stopniach
            radius = self.spiral_step * (angle / 360.0)
            
            if radius > self.max_radius:
                break
                
            # Przeliczenie na współrzędne kartezjańskie (w stopniach)
            angle_rad = math.radians(angle)
            delta_az = radius * math.cos(angle_rad)
            delta_el = radius * math.sin(angle_rad)
            
            # Kompensacja dla małych kątów elewacji (projekcja sferyczna)
            delta_az = delta_az / math.cos(math.radians(center_el))
            
            az = center_az + delta_az
            el = center_el + delta_el
            
            # Sprawdzenie limitów
            if 0 <= az <= 360 and -5 <= el <= 97:
                points.append((az, el))
        
        logger.info(f"Wygenerowano {len(points)} punktów spirali")
        return points
    
    def measure_signal_strength(self, az, el, measurement_time_utc):
        """
        Symuluje pomiar mocy sygnału w danej pozycji.
        W rzeczywistości tutaj byłby odczyt z SDR/odbiornika.
        
        Args:
            az: Azymut w stopniach
            el: Elewacja w stopniach
            measurement_time_utc: Czas pomiaru (datetime) dla wyliczenia pozycji Słońca
        
        Dla symulacji: moc maleje z odległością od prawdziwej pozycji.
        """
        # WAŻNE: Pobierz świeżą pozycję Słońca dla aktualnego czasu pomiaru
        # Słońce porusza się około 15°/godzinę w azymucie (w zależności od szerokości geograficznej)
        sun_pos = self.astro_calc.calculate_object_position(AstronomicalObjectType.SUN)
        
        # W symulatorze zakładamy, że prawdziwa pozycja jest przesunięta
        # o pewien offset (który chcemy znaleźć)
        # Dla przykładu: prawdziwa pozycja = teoretyczna + (5°, 2°)
        true_sun_az = sun_pos.azimuth + 5.0  # Symulowany offset azymutu
        true_sun_el = sun_pos.elevation + 2.0  # Symulowany offset elewacji
        
        # Oblicz odległość kątową od prawdziwej pozycji
        delta_az = (az - true_sun_az) * math.cos(math.radians(el))
        delta_el = el - true_sun_el
        distance = math.sqrt(delta_az**2 + delta_el**2)
        
        # Moc maleje gaussowsko z odległością
        # Szerokość wiązki słońca na częstotliwości ~1.4 GHz to około 0.5° (FWHM)
        beam_width = 0.5
        signal_strength = 100.0 * math.exp(-0.5 * (distance / beam_width)**2)
        
        # Dodaj szum pomiarowy
        import random
        noise = random.gauss(0, 5)
        signal_strength += noise
        
        logger.info(
            "  [%s] Pozycja: Az=%.2f deg, El=%.2f deg | "
            "Slonce(teor): Az=%.2f deg, El=%.2f deg | Moc: %.2f dB",
            measurement_time_utc.strftime("%H:%M:%S"),
            az, el, sun_pos.azimuth, sun_pos.elevation, signal_strength
        )
        
        return signal_strength, sun_pos
    
    def move_and_measure(self, az, el):
        """Przesuwa antenę i wykonuje pomiar."""
        logger.info("Przesuwam antene do: Az=%.2f deg, El=%.2f deg", az, el)
        
        # Przesuń antenę
        target = Position(azimuth=az, elevation=el)
        self.antenna.move_to(target)
        
        # Czekaj aż antena dojedzie i ustabilizuje się
        while self.antenna.state == AntennaState.MOVING:
            time.sleep(0.1)
        
        # Dodatkowy czas na stabilizację
        time.sleep(self.measurement_time)
        
        # Wykonaj pomiar z aktualnym czasem
        measurement_time = datetime.now()
        signal, sun_pos_at_measurement = self.measure_signal_strength(az, el, measurement_time)
        
        return signal, sun_pos_at_measurement
    
    def run_spiral_scan(self):
        """Przeprowadza pełen spiralny skan."""
        logger.info("=" * 70)
        logger.info("Rozpoczynam spiralny skan kalibracyjny Slonca")
        logger.info("=" * 70)
        
        # Pobierz startową pozycję Słońca (tylko do wygenerowania punktów spirali)
        start_time = datetime.now()
        sun_pos_start = self.get_sun_position()
        logger.info(
            "Pozycja Slonca na start skanu [%s]: Az=%.2f deg, El=%.2f deg",
            start_time.strftime("%H:%M:%S"),
            sun_pos_start.azimuth,
            sun_pos_start.elevation
        )
        
        # Wygeneruj punkty spirali wokół startowej pozycji
        points = self.generate_spiral_points(sun_pos_start.azimuth, sun_pos_start.elevation)
        
        # Oblicz szacowany czas trwania skanu
        estimated_time = len(points) * (self.measurement_time + 2)  # +2s na ruch
        logger.info(
            "Wygenerowano %d punktow spirali. Szacowany czas: %.1f min",
            len(points),
            estimated_time / 60.0
        )
        
        # Wykonaj pomiary
        logger.info("\nWykonuje pomiary...")
        
        for i, (az, el) in enumerate(points, 1):
            logger.info("\n[Punkt %d/%d]", i, len(points))
            
            # Wykonaj pomiar - funkcja move_and_measure pobierze świeżą pozycję Słońca
            signal, sun_pos_at_measurement = self.move_and_measure(az, el)
            
            self.measurements.append({
                'azimuth': az,
                'elevation': el,
                'signal': signal,
                'sun_azimuth': sun_pos_at_measurement.azimuth,
                'sun_elevation': sun_pos_at_measurement.elevation,
                'timestamp': datetime.now().isoformat()
            })
            
            # Aktualizuj najlepszą pozycję
            if signal > self.best_signal:
                self.best_signal = signal
                self.best_position = (az, el)
                self.best_sun_position = sun_pos_at_measurement
                logger.info("  >>> Nowa najlepsza pozycja! Moc: %.2f dB", signal)
        
        # Podsumowanie ruchu Słońca podczas skanu
        end_time = datetime.now()
        sun_pos_end = self.get_sun_position()
        sun_movement_az = sun_pos_end.azimuth - sun_pos_start.azimuth
        sun_movement_el = sun_pos_end.elevation - sun_pos_start.elevation
        
        logger.info("\n" + "=" * 70)
        logger.info("Skan zakonczony!")
        logger.info("Czas trwania: %.1f min", (end_time - start_time).total_seconds() / 60.0)
        logger.info(
            "Ruch Slonca podczas skanu: Az: %+.3f deg, El: %+.3f deg",
            sun_movement_az,
            sun_movement_el
        )
        logger.info("=" * 70)
    
    def calculate_offset(self):
        """Oblicza offset na podstawie wyników skanu."""
        if not self.best_position:
            logger.error("Brak danych z pomiarów!")
            return None, None
        
        sun_pos = self.get_sun_position()
        measured_az, measured_el = self.best_position
        
        offset_az = measured_az - sun_pos.azimuth
        offset_el = measured_el - sun_pos.elevation
        
        logger.info(f"\n Wyniki kalibracji:")
        logger.info(f"   Pozycja teoretyczna: Az={sun_pos.azimuth:.2f}°, El={sun_pos.elevation:.2f}°")
        logger.info(f"   Pozycja zmierzona:   Az={measured_az:.2f}°, El={measured_el:.2f}°")
        logger.info(f"   Maksymalna moc:      {self.best_signal:.2f} dB")
        logger.info(f"\n Obliczony offset:")
        logger.info(f"   Azymut:   {offset_az:+.2f}°")
        logger.info(f"   Elewacja: {offset_el:+.2f}°")
        
        return offset_az, offset_el
    
    def save_calibration(self, offset_az, offset_el):
        """Zapisuje obliczony offset używając PositionCalibration."""
        calib_file = str(Path(__file__).parent.parent / "resource" / "antenna_calibration.json")
        
        try:
            # Pobierz aktualną kalibrację z kontrolera
            current_cal = self.antenna.position_calibration
            
            # Utwórz nową kalibrację z obliczonymi offsetami
            new_calibration = PositionCalibration(
                azimuth_offset=round(offset_az, 2),
                elevation_offset=round(offset_el, 2),
                min_azimuth=current_cal.min_azimuth,
                max_azimuth=current_cal.max_azimuth,
                min_elevation=current_cal.min_elevation,
                max_elevation=current_cal.max_elevation
            )
            
            # Zapisz do pliku używając metody z PositionCalibration
            new_calibration.save_to_file(calib_file)
            
            # Ustaw nową kalibrację w kontrolerze
            self.antenna.set_position_calibration(new_calibration, save_to_file=False)
            
            logger.info(f"\n💾 Kalibracja zapisana do: {calib_file}")
            logger.info(f"   azimuth_offset: {offset_az:.2f}°")
            logger.info(f"   elevation_offset: {offset_el:.2f}°")
            
            return True
        except Exception as e:
            logger.error(f"Błąd zapisu kalibracji: {e}", exc_info=True)
            return False
    
    def export_results(self):
        """Eksportuje szczegółowe wyniki do pliku CSV."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = Path(__file__).parent / f"spiral_scan_results_{timestamp}.csv"
        
        try:
            with open(results_file, 'w') as f:
                f.write("azimuth,elevation,signal_strength\n")
                for m in self.measurements:
                    f.write(f"{m['azimuth']:.4f},{m['elevation']:.4f},{m['signal']:.4f}\n")
            
            logger.info(f"📈 Szczegółowe wyniki zapisane do: {results_file}")
            return True
        except Exception as e:
            logger.error(f"Błąd zapisu wyników: {e}")
            return False


def main():
    """Główna funkcja programu."""
    print("\n" + "=" * 70)
    print("Program automatycznej kalibracji spiralnej - Słońce")
    print("=" * 70)
    logger.info(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Inicjalizacja
    language_helper = LanguageHelper(language="pl", defaultLanguage="en")
    
    # Wybór lokalizacji
    print("\nDostępne lokalizacje:")
    for key, obs in OBSERVATORIES.items():
        print(f"  {key}: {obs['name']} ({obs['latitude']:.4f}°N, {obs['longitude']:.4f}°E)")
    
    location_key = input("\nWybierz lokalizację (domyślnie: polanka): ").strip().lower() or "polanka"
    
    if location_key not in OBSERVATORIES:
        logger.warning(f"Nieznana lokalizacja '{location_key}', używam domyślnej: polanka")
        location_key = "polanka"
    
    observer = get_observer_location(location_key, language_helper)
    
    logger.info(f"✓ Lokalizacja: {observer.name}")
    logger.info(f"  Współrzędne: {observer.latitude:.4f}°N, {observer.longitude:.4f}°E")
    logger.info(f"  Wysokość: {observer.elevation:.1f}m n.p.m.\n")
    
    # Tworzenie kontrolera anteny
    use_simulator = input("Użyć symulatora? (T/n): ").strip().lower() != 'n'
    
    factory = AntennaControllerFactory(language_helper)
    
    if use_simulator:
        antenna = factory.create_simulator_controller(
            simulation_speed=1000.0,
            motor_config=MotorConfig()
        )
        logger.info("✓ Kontroler anteny zainicjalizowany (SYMULATOR)")
    else:
        # Użyj prawdziwego kontrolera
        port = input("Podaj port (Enter = auto): ").strip() or None
        antenna = factory.create_spid_controller(
            port=port,
            motor_config=MotorConfig()
        )
        logger.info(f"✓ Kontroler anteny zainicjalizowany (SPID na {port or 'auto'})")
    
    antenna.initialize()
    
    # Parametry skanu
    print("\nParametry spiralnego skanu:")
    spiral_step = float(input("  Krok spirali w stopniach (domyślnie 0.5): ") or "0.5")
    max_radius = float(input("  Maksymalny promień spirali w stopniach (domyślnie 10.0): ") or "10.0")
    measurement_time = float(input("  Czas pomiaru na punkt w sekundach (domyślnie 2.0): ") or "2.0")
    
    # Utwórz obiekt kalibracji
    calibration = SpiralSunCalibration(
        antenna_controller=antenna,
        observer_location=observer,
        use_sdr=False  # TODO: Dodać obsługę SDR
    )
    
    # Ustaw parametry
    calibration.spiral_step = spiral_step
    calibration.max_radius = max_radius
    calibration.measurement_time = measurement_time
    
    logger.info(f"\n✓ Parametry skanu: krok={spiral_step}°, promień={max_radius}°, czas={measurement_time}s\n")
    
    input("Naciśnij Enter, aby rozpocząć skan kalibracyjny...")
    
    # Wykonaj spiralny skan
    try:
        calibration.run_spiral_scan()
        
        # Oblicz offset
        offset_az, offset_el = calibration.calculate_offset()
        
        if offset_az is not None:
            # Zapisz kalibrację
            save = input("\nZapisać kalibrację do pliku? (T/n): ").strip().lower() != 'n'
            
            if save:
                calibration.save_calibration(offset_az, offset_el)
            else:
                logger.info("\nKalibracja NIE została zapisana")
            
            # Eksportuj szczegółowe wyniki
            export = input("Eksportować szczegółowe wyniki do CSV? (T/n): ").strip().lower() != 'n'
            if export:
                calibration.export_results()
            
            logger.info("\n Kalibracja zakończona sukcesem!")
        else:
            logger.error("\n Kalibracja nie powiodła się!")
            
    except KeyboardInterrupt:
        logger.info("\n\n  Przerwano przez użytkownika")
    except Exception as e:
        logger.error(f"\n Błąd podczas kalibracji: {e}", exc_info=True)
    finally:
        # Zatrzymaj antenę
        try:
            antenna.stop()
            logger.info("\n Antena zatrzymana")
        except:
            pass
    
    print("\n" + "=" * 70)
    print("Program kalibracji spiralnej - KONIEC")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
