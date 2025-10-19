import asyncio
import logging
from typing import Optional

from fastapi.responses import JSONResponse
from fastapi import HTTPException

from backend.Engine.Antenna import AntennaControllerFactory, DEFAULT_SPID_PORT, DEFAULT_BAUDRATE, AntennaController, \
    AntennaControllerService
from backend.Engine.Antenna.AntennaControllerHelper import AntennaState
from backend.Engine.Antenna.Model import PositionModel, ObserverLocationModel, StatusResponse, ConnectionConfigModel, \
    AxisMoveModel, CalibrationModel, AzimuthCalibrationModel, TrackingConfigModel
from backend.Engine.Antenna.Motor.MotorConfig import MotorConfig
from backend.Engine.Antenna.Position import Position, PositionCalibration


from backend.Engine.AstronomyCalculator import AstronomicalCalculator, ObserverLocation, \
    AstronomicalObjectType, AstronomicalTracker

class EngineServiceRest:
    __logger = logging.getLogger(__name__)

    __antenna_controller: Optional[AntennaController] = None
    __antennaControllerService: AntennaControllerService = None
    __astro_calculator: Optional[AstronomicalCalculator] = None
    __current_observer_location: Optional[ObserverLocation] = None
    __astro_tracker: Optional[AstronomicalTracker] = None
    __tracking_active: bool = False
    __tracking_task: Optional[asyncio.Task] = None
    __current_port: Optional[str] = None

    def emergency_stop(self, port = DEFAULT_SPID_PORT, speed: int = DEFAULT_BAUDRATE) -> bool:
        success = False
        self.__logger.warning(f'Emergency stop. Used port for Hamlib: {port}')

        if not self.__antennaControllerService.check_rotctl():
            self.__logger.error("rotctl (Hamlib) nie jest dostępne w systemie")
        else:
            result = self.__antennaControllerService.stop_rotor_move_rotctl(port, speed)

            if "OK" in result or "STOP" in result:
                self.__logger.info(f"Successfully stopped: {result.strip()}")
                success = True
            else:
                self.__logger.error(f"Error during emergency stop: {result.strip()}")

        return success

    def get_status(self):
        """Pobierz aktualny status systemu anteny"""

        connected = (self.__antenna_controller is not None and
                     hasattr(self.__antenna_controller.motor_driver, 'connected') and
                     self.__antenna_controller.motor_driver.connected)
        current_position = None
        is_moving = False
        last_error = None

        if connected:
            try:
                # Użyj get_current_position() z kalibracją zamiast raw current_position
                pos = self.__antenna_controller.get_current_position(apply_reverse_calibration=True)
                if pos:
                    current_position = PositionModel(azimuth=pos.azimuth, elevation=pos.elevation)
                is_moving = self.__antenna_controller.state == AntennaState.MOVING
            except Exception as e:
                last_error = str(e)
                self.__logger.error(f"Błąd pobierania statusu: {e}")

        observer_loc = None
        if self.__current_observer_location:
            observer_loc = ObserverLocationModel(
                latitude=self.__current_observer_location.latitude,
                longitude=self.__current_observer_location.longitude,
                elevation=self.__current_observer_location.elevation,
                name=self.__current_observer_location.name
            )

        return StatusResponse(
            connected=connected,
            current_position=current_position,
            is_moving=is_moving,
            last_error=last_error,
            observer_location=observer_loc,
            port=self.__current_port
        )

    def connect_antenna(self, config: ConnectionConfigModel):
        """Nawiąż połączenie z anteną"""
        try:
            if config.use_simulator:
                self.__logger.info("Łączę z symulatorem...")
                self.__antenna_controller = AntennaControllerFactory.create_simulator_controller(
                    simulation_speed=2000.0,
                    motor_config=MotorConfig()
                )
                self.__current_port = "Symulator"
            else:
                port = config.port
                if not port:
                    # Użyj domyślnego portu lub najlepszego dostępnego
                    self.__logger.info("Szukam najlepszego portu SPID...")
                    port = self.__antennaControllerService.get_best_spid_port()
                    self.__logger.info(f"Wybrany port: {port}")

                self.__logger.info(f"Łączę z portem {port}...")
                self.__antenna_controller = AntennaControllerFactory.create_spid_controller(
                    port=port,
                    baudrate=config.baudrate,
                    motor_config=MotorConfig()
                )
                self.__current_port = port

            # Inicjalizuj kontroler
            self.__antenna_controller.initialize()

            self.__logger.info("Połączenie nawiązane pomyślnie")
            return {"status": "connected", "port": self.__current_port, "simulator": config.use_simulator}

        except Exception as e:
            self.__logger.error(f"Błąd połączenia: {e}")
            raise HTTPException(status_code=500, detail=f"Błąd połączenia: {str(e)}")


    def disconnect_antenna(self):
        """Rozłącz z anteną"""
        try:
            if self.__antenna_controller:
                self.__antenna_controller.stop()
                self.__antenna_controller.shutdown()
                antenna_controller = None
                current_port = None

            self.__logger.info("Rozłączono z anteną")
            return {"status": "disconnected"}

        except Exception as e:
            self.__logger.error(f"Błąd rozłączania: {e}")
            raise HTTPException(status_code=500, detail=f"Błąd rozłączania: {str(e)}")

    def get_position(self):
        """Pobierz aktualną pozycję anteny (skalibrowaną)"""
        controller = self.__get_antenna_controller()

        try:
            # Użyj get_current_position() z kalibracją zamiast raw current_position
            pos = controller.get_current_position(apply_reverse_calibration=True)
            if pos is None:
                raise HTTPException(status_code=404, detail="Nie można pobrać pozycji")

            return PositionModel(azimuth=pos.azimuth, elevation=pos.elevation)

        except Exception as e:
            self.__logger.error(f"Błąd pobierania pozycji: {e}")
            raise HTTPException(status_code=500, detail=f"Błąd pobierania pozycji: {str(e)}")


    def set_position(self, position: PositionModel):
        """Ustaw nową pozycję anteny"""
        controller = self.__get_antenna_controller()

        try:
            target_pos = Position(position.azimuth, position.elevation)
            controller.move_to(target_pos)

            return {"status": "moving", "target": position.model_dump()}

        except Exception as e:
            self.__logger.error(f"Błąd ustawiania pozycji: {e}")
            raise HTTPException(status_code=500, detail=f"Błąd ustawiania pozycji: {str(e)}")


    def stop_antenna(self):
        """Natychmiastowe zatrzymanie anteny"""
        controller = self.__get_antenna_controller()

        try:
            controller.stop()
            self.__logger.info("Antena zatrzymana")
            return {"status": "stopped"}

        except Exception as e:
            self.__logger.error(f"Błąd zatrzymywania: {e}")
            raise HTTPException(status_code=500, detail=f"Błąd zatrzymywania: {str(e)}")


    def set_observer_location(self, location: ObserverLocationModel):
        """Ustaw lokalizację obserwatora dla obliczeń astronomicznych"""

        try:
            self.__current_observer_location = ObserverLocation(
                latitude=location.latitude,
                longitude=location.longitude,
                elevation=location.elevation,
                name=location.name
            )

            self.__astro_calculator = AstronomicalCalculator(self.__current_observer_location)
            self.__astro_tracker = AstronomicalTracker(self.__astro_calculator)

            self.__logger.info(f"Ustawiono lokalizację obserwatora: {location.name}")
            return {"status": "set", "location": location.model_dump()}

        except Exception as e:
            self.__logger.error(f"Błąd ustawiania lokalizacji: {e}")
            raise HTTPException(status_code=500, detail=f"Błąd ustawiania lokalizacji: {str(e)}")


    def get_observer_location(self):
        """Pobierz aktualną lokalizację obserwatora"""

        if self.__current_observer_location is None:
            raise HTTPException(status_code=404, detail="Lokalizacja obserwatora nie jest ustawiona")

        return ObserverLocationModel(
            latitude=self.__current_observer_location.latitude,
            longitude=self.__current_observer_location.longitude,
            elevation=self.__current_observer_location.elevation,
            name=self.__current_observer_location.name
        )

    def track_object(self, object_name: str, object_type: AstronomicalObjectType = AstronomicalObjectType.SUN):
        """Rozpocznij śledzenie obiektu astronomicznego"""
        controller = self.__get_antenna_controller()
        calculator = self.__get_astro_calculator()

        try:
            # Oblicz pozycję obiektu
            if object_type == AstronomicalObjectType.SUN:
                position = calculator.get_sun_position()
            elif object_type == AstronomicalObjectType.MOON:
                position = calculator.get_moon_position()
            elif object_name.lower() in ["mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune"]:
                planet_type = AstronomicalObjectType(object_name.lower())
                position = calculator.get_planet_position(planet_type)
            else:
                position = calculator.get_star_position(object_name)

            if position is None or not position.is_visible:
                raise HTTPException(status_code=404, detail=f"Obiekt {object_name} nie jest widoczny")

            # Konwertuj na pozycję anteny i przesuń
            antenna_position = position.to_antenna_position()
            if antenna_position:
                controller.move_to(antenna_position)
            else:
                raise HTTPException(status_code=400, detail=f"Obiekt {object_name} jest poza zasięgiem anteny")

            self.__logger.info(f"Przesunięto antenę do obiektu: {object_name}")
            return {
                "status": "moved_to_object",
                "object": object_name,
                "type": object_type.value,
                "position": {"azimuth": position.azimuth, "elevation": position.elevation}
            }

        except Exception as e:
            self.__logger.error(f"Błąd pozycjonowania na obiekt: {e}")
            raise HTTPException(status_code=500, detail=f"Błąd pozycjonowania na obiekt: {str(e)}")


    def start_tracking(self, config: TrackingConfigModel):
        """Rozpocznij ciągłe śledzenie obiektu astronomicznego"""
        if self.__tracking_active:
            raise HTTPException(status_code=400, detail="Śledzenie już jest aktywne. Zatrzymaj je najpierw.")

        try:
            # Sprawdź dostępność wymaganych komponentów
            self.__get_antenna_controller()
            self.__get_astro_tracker()

            self.__tracking_active = True
            self.__tracking_task = asyncio.create_task(self.__continuous_tracking_task(config))

            self.__logger.info(f"Rozpoczęto ciągłe śledzenie obiektu: {config.object_name}")
            return {
                "status": "tracking_started",
                "object": config.object_name,
                "type": config.object_type.value,
                "config": config.model_dump()
            }

        except Exception as e:
            self.__tracking_active = False
            self.__logger.error(f"Błąd rozpoczęcia śledzenia: {e}")
            raise HTTPException(status_code=500, detail=f"Błąd rozpoczęcia śledzenia: {str(e)}")


    async def stop_tracking(self):
        """Zatrzymaj śledzenie obiektu"""
        try:
            if self.__tracking_active:
                self.__tracking_active = False
                if self.__tracking_task and not self.__tracking_task.done():
                    self.__tracking_task.cancel()
                    try:
                        await self.__tracking_task
                    except asyncio.CancelledError:
                        pass
                self.__tracking_task = None

            # Zatrzymaj też antenę
            controller = self.__get_antenna_controller()
            controller.stop()

            self.__logger.info("Zatrzymano śledzenie")
            return {"status": "tracking_stopped"}

        except Exception as e:
            self.__logger.error(f"Błąd zatrzymywania śledzenia: {e}")
            raise HTTPException(status_code=500, detail=f"Błąd zatrzymywania śledzenia: {str(e)}")


    def get_tracking_status(self):
        """Pobierz aktualny status śledzenia"""
        return {
            "self.__tracking_active": self.__tracking_active,
            "task_running": self.__tracking_task is not None and not self.__tracking_task.done() if self.__tracking_task else False
        }


    def list_ports(self):
        """Lista dostępnych portów szeregowych"""
        try:
            # Zwróć domyślny port SPID
            return {"ports": [DEFAULT_SPID_PORT], "default_port": DEFAULT_SPID_PORT}

        except Exception as e:
            self.__logger.error(f"Błąd listowania portów: {e}")
            raise HTTPException(status_code=500, detail=f"Błąd listowania portów: {str(e)}")


    def diagnostic(self):
        """Sprawdź, czy rotctl i SPID działają"""
        try:
            rotctl_available = self.__antennaControllerService.check_rotctl()
            spid_connected = self.__antennaControllerService.test_spid_connection(DEFAULT_SPID_PORT, DEFAULT_BAUDRATE)

            return {
                "rotctl_available": rotctl_available,
                "rotctl_version": "Available" if rotctl_available else "N/A",
                "spid_connected": spid_connected,
                "spid_error": "SPID not responding" if not spid_connected else "OK",
                "default_port": DEFAULT_SPID_PORT,
                "recommendation": ("Użyj symulatora jeśli SPID nie odpowiada"
                                   if not spid_connected else "SPID ready")
            }

        except Exception as e:
            self.__logger.error(f"Błąd diagnostyki: {e}")
            raise HTTPException(status_code=500, detail=f"Błąd diagnostyki: {str(e)}")


    def get_astronomical_position(self, object_name: str):
        """Pobierz aktualną pozycję obiektu astronomicznego"""
        calculator = self.__get_astro_calculator()

        try:
            object_name_lower = object_name.lower()

            # Mapowanie obiektów na właściwe typy
            if object_name_lower == "sun":
                position = calculator.get_sun_position()
            elif object_name_lower == "moon":
                position = calculator.get_moon_position()
            elif object_name_lower in ["mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune"]:
                # Konwertuj nazwę na AstronomicalObjectType
                planet_type = AstronomicalObjectType(object_name_lower)
                position = calculator.get_planet_position(planet_type)
            else:
                # Dla gwiazd i innych obiektów
                position = calculator.get_star_position(object_name)

            if position is None:
                raise HTTPException(status_code=404, detail=f"Nie można obliczyć pozycji dla obiektu: {object_name}")

            if not position.is_visible:
                self.__logger.warning(f"Obiekt {object_name} jest pod horyzontem")

            # Konwertuj do pozycji anteny (z właściwą konwersją elewacji)
            antenna_position = position.to_antenna_position()
            if antenna_position is None:
                # Obiekt nie jest widoczny, ale zwróć surowe dane
                converted_elevation = 90.0 - position.elevation if position.elevation >= 0 else position.elevation
            else:
                converted_elevation = antenna_position.elevation

            return {
                "azimuth": position.azimuth,
                "elevation": converted_elevation,
                "distance": position.distance,
                "ra": position.ra,
                "dec": position.dec,
                "is_visible": position.is_visible,
                "magnitude": position.magnitude if hasattr(position, 'magnitude') else None
            }

        except ValueError:
            self.__logger.error(f"Nieprawidłowy obiekt astronomiczny: {object_name}")
            raise HTTPException(status_code=400, detail=f"Nieprawidłowy obiekt astronomiczny: {object_name}")
        except Exception as e:
            self.__logger.error(f"Błąd obliczania pozycji obiektu {object_name}: {e}")
            raise HTTPException(status_code=500, detail=f"Błąd obliczania pozycji: {str(e)}")


    def calibrate_azimuth_reference(self, calibration: AzimuthCalibrationModel):
        """Kalibruje punkt referencyjny azymutu (ustala nowe 0°)"""
        controller = self.__get_antenna_controller()

        try:
            controller.calibrate_azimuth_reference(
                current_azimuth=calibration.current_azimuth,
                save_to_file=calibration.save_to_file
            )

            self.__logger.info(f"Kalibracja azymutu wykonana. Offset: {controller.position_calibration.azimuth_offset:.2f}°")
            return {
                "status": "calibrated",
                "azimuth_offset": controller.position_calibration.azimuth_offset,
                "saved_to_file": calibration.save_to_file
            }

        except Exception as e:
            self.__logger.error(f"Błąd kalibracji azymutu: {e}")
            raise HTTPException(status_code=500, detail=f"Błąd kalibracji azymutu: {str(e)}")


    def get_calibration(self):
        """Pobierz aktualne parametry kalibracji"""
        controller = self.__get_antenna_controller()

        try:
            cal = controller.position_calibration
            return CalibrationModel(
                azimuth_offset=cal.azimuth_offset,
                elevation_offset=cal.elevation_offset
            )

        except Exception as e:
            self.__logger.error(f"Błąd pobierania kalibracji: {e}")
            raise HTTPException(status_code=500, detail=f"Błąd pobierania kalibracji: {str(e)}")


    def set_calibration(self, calibration: CalibrationModel):
        """Ustaw parametry kalibracji"""
        controller = self.__get_antenna_controller()

        try:
            new_cal = PositionCalibration(
                azimuth_offset=calibration.azimuth_offset,
                elevation_offset=calibration.elevation_offset
            )

            controller.set_position_calibration(new_cal, save_to_file=True)

            self.__logger.info("Kalibracja została ustawiona i zapisana")
            return {"status": "set", "calibration": calibration.model_dump()}

        except Exception as e:
            self.__logger.error(f"Błąd ustawiania kalibracji: {e}")
            raise HTTPException(status_code=500, detail=f"Błąd ustawiania kalibracji: {str(e)}")


    def reset_calibration(self):
        """Resetuj kalibrację do wartości domyślnych"""
        controller = self.__get_antenna_controller()

        try:
            controller.reset_calibration(save_to_file=True)
            self.__logger.info("Kalibracja została zresetowana do wartości domyślnych")
            return {"status": "reset", "message": "Kalibracja zresetowana do wartości domyślnych"}

        except Exception as e:
            self.__logger.error(f"Błąd resetowania kalibracji: {e}")
            raise HTTPException(status_code=500, detail=f"Błąd resetowania kalibracji: {str(e)}")


    def move_axis(self, move: AxisMoveModel):
        """Porusz anteną w określonej osi o zadaną wartość"""
        controller = self.__get_antenna_controller()

        try:
            # Użyj skalibrowanej pozycji do obliczeń
            current_pos = controller.get_current_position(apply_reverse_calibration=True)

            if move.axis.lower() == "azimuth":
                if move.direction.lower() == "positive":
                    new_azimuth = (current_pos.azimuth + move.amount) % 360
                else:  # negative
                    new_azimuth = (current_pos.azimuth - move.amount) % 360
                new_position = Position(azimuth=new_azimuth, elevation=current_pos.elevation)

            elif move.axis.lower() == "elevation":
                if move.direction.lower() == "positive":
                    new_elevation = current_pos.elevation + move.amount
                else:  # negative
                    new_elevation = current_pos.elevation - move.amount
                new_position = Position(azimuth=current_pos.azimuth, elevation=new_elevation)

            else:
                raise HTTPException(status_code=400, detail="Oś musi być 'azimuth' lub 'elevation'")

            controller.move_to(new_position)

            self.__logger.info(f"Ruch w osi {move.axis}: {move.direction} o {move.amount}°")
            return {
                "status": "moving",
                "axis": move.axis,
                "direction": move.direction,
                "amount": move.amount,
                "new_position": {"azimuth": new_position.azimuth, "elevation": new_position.elevation}
            }

        except Exception as e:
            self.__logger.error(f"Błąd ruchu w osi: {e}")
            raise HTTPException(status_code=500, detail=f"Błąd ruchu w osi: {str(e)}")

    # Pomocnicze funkcje
    def __get_antenna_controller(self) -> AntennaController:
        """Pobiera kontroler anteny lub rzuca wyjątek HTTP jeśli nie jest zainicjalizowany"""
        if self.__antenna_controller is None:
            raise HTTPException(status_code=503, detail="Kontroler anteny nie jest zainicjalizowany. Użyj /connect")
        return self.__antenna_controller

    def __get_astro_calculator(self) -> AstronomicalCalculator:
        """Pobiera kalkulator astronomiczny lub rzuca wyjątek HTTP jeśli nie jest skonfigurowany"""
        if self.__astro_calculator is None or self.__current_observer_location is None:
            raise HTTPException(status_code=503,
                                detail="Kalkulator astronomiczny nie jest skonfigurowany. Ustaw lokalizację obserwatora")
        return self.__astro_calculator

    def __get_astro_tracker(self) -> AstronomicalTracker:
        """Pobiera tracker astronomiczny lub rzuca wyjątek HTTP jeśli nie jest skonfigurowany"""
        if self.__astro_tracker is None:
            raise HTTPException(status_code=503,
                                detail="Tracker astronomiczny nie jest skonfigurowany. Ustaw lokalizację obserwatora")
        return self.__astro_tracker

    async def __continuous_tracking_task(self, tracking_config: TrackingConfigModel):
        """Zadanie ciągłego śledzenia obiektu astronomicznego"""
        self.__logger.info(f"Rozpoczęcie ciągłego śledzenia obiektu: {tracking_config.object_name}")

        try:
            tracker = self.__get_astro_tracker()
            controller = self.__get_antenna_controller()

            # Utwórz funkcję śledzenia dla określonego obiektu
            if tracking_config.object_type == AstronomicalObjectType.SUN:
                track_function = tracker.track_sun()
            elif tracking_config.object_type == AstronomicalObjectType.MOON:
                track_function = tracker.track_moon()
            elif tracking_config.object_type in [
                AstronomicalObjectType.MERCURY,
                AstronomicalObjectType.VENUS,
                AstronomicalObjectType.MARS,
                AstronomicalObjectType.JUPITER,
                AstronomicalObjectType.SATURN,
                AstronomicalObjectType.URANUS,
                AstronomicalObjectType.NEPTUNE
            ]:
                # Planety
                track_function = tracker.track_planet(tracking_config.object_type)
            elif tracking_config.object_type == AstronomicalObjectType.STAR:
                # Gwiazdy
                track_function = tracker.track_star(tracking_config.object_name)
            elif tracking_config.object_type == AstronomicalObjectType.CUSTOM:
                # Obiekt niestandardowy - wymaga współrzędnych
                raise HTTPException(status_code=400,
                                    detail="Śledzenie obiektów niestandardowych wymaga podania współrzędnych")
            else:
                # Próba automatycznego rozpoznania typu na podstawie nazwy
                object_name_lower = tracking_config.object_name.lower()
                if object_name_lower == "sun":
                    track_function = tracker.track_sun()
                elif object_name_lower == "moon":
                    track_function = tracker.track_moon()
                elif object_name_lower in ["mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune"]:
                    planet_type = AstronomicalObjectType(object_name_lower)
                    track_function = tracker.track_planet(planet_type)
                else:
                    # Domyślnie traktuj jako gwiazdę
                    track_function = tracker.track_star(tracking_config.object_name)

            while self.__tracking_active:
                try:
                    # Pobierz aktualną pozycję obiektu
                    target_position = track_function()

                    if target_position is None:
                        self.__logger.warning(f"Obiekt {tracking_config.object_name} jest poza zasięgiem")
                        break

                    self.__logger.info(
                        f"Śledzenie {tracking_config.object_name}: Az={target_position.azimuth:.2f}°, El={target_position.elevation:.2f}°")

                    # Po prostu przesuń antenę do nowej pozycji co określony czas
                    controller.move_to(target_position)
                    self.__logger.info(
                        f"Przesunięto antenę do pozycji: Az={target_position.azimuth:.2f}°, El={target_position.elevation:.2f}°")

                    # Czekaj przez określony interwał
                    await asyncio.sleep(tracking_config.update_interval)

                except Exception as e:
                    self.__logger.error(f"Błąd podczas śledzenia: {e}")
                    await asyncio.sleep(5)  # Krótsza pauza przy błędzie

        except Exception as e:
            self.__logger.error(f"Krytyczny błąd śledzenia: {e}")
        finally:
            self.__tracking_active = False
            self.__logger.info(f"Zakończono śledzenie obiektu: {tracking_config.object_name}")
