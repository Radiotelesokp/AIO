import logging
from fastapi.responses import JSONResponse
from fastapi import HTTPException
from backend.Engine.antenna_controller import DEFAULT_SPID_PORT, rotctl_zatrzymaj_rotor, sprawdz_rotctl, \
    DEFAULT_BAUDRATE

from backend.Engine.AstronomyCalculator import AstronomicalCalculator, ObserverLocation, \
    AstronomicalObjectType, AstronomicalTracker

class EngineService:
    __logger = logging.getLogger(__name__)

    def emergency_stop(self, port = DEFAULT_SPID_PORT, speed: int = DEFAULT_BAUDRATE) -> bool:
        success = False
        self.__logger.warning(f'Emergency stop. Used port for Hamlib: {port}')

        if not sprawdz_rotctl():
            self.__logger.error("rotctl (Hamlib) nie jest dostępne w systemie")
        else:
            result = rotctl_zatrzymaj_rotor(port, speed)

            if "OK" in result or "STOP" in result:
                self.__logger.info(f"Successfully stopped: {result.strip()}")
                success = True
            else:
                self.__logger.error(f"Error during emergency stop: {result.strip()}")

        return success

    def get_status(self):
        """Pobierz aktualny status systemu anteny"""
        global antenna_controller, current_observer_location

        connected = (antenna_controller is not None and
                     hasattr(antenna_controller.motor_driver, 'connected') and
                     antenna_controller.motor_driver.connected)
        current_position = None
        is_moving = False
        last_error = None

        if connected:
            try:
                # Użyj get_current_position() z kalibracją zamiast raw current_position
                pos = antenna_controller.get_current_position(apply_reverse_calibration=True)
                if pos:
                    current_position = PositionModel(azimuth=pos.azimuth, elevation=pos.elevation)
                is_moving = antenna_controller.state == AntennaState.MOVING
            except Exception as e:
                last_error = str(e)
                self.__logger.error(f"Błąd pobierania statusu: {e}")

        observer_loc = None
        if current_observer_location:
            observer_loc = ObserverLocationModel(
                latitude=current_observer_location.latitude,
                longitude=current_observer_location.longitude,
                elevation=current_observer_location.elevation,
                name=current_observer_location.name
            )

        return StatusResponse(
            connected=connected,
            current_position=current_position,
            is_moving=is_moving,
            last_error=last_error,
            observer_location=observer_loc,
            port=current_port
        )

    def connect_antenna(self, config: ConnectionConfigModel):
        """Nawiąż połączenie z anteną"""
        global antenna_controller, current_port

        try:
            if config.use_simulator:
                self.__logger.info("Łączę z symulatorem...")
                antenna_controller = AntennaControllerFactory.create_simulator_controller(
                    simulation_speed=2000.0,
                    motor_config=MotorConfig()
                )
                current_port = "Symulator"
            else:
                port = config.port
                if not port:
                    # Użyj domyślnego portu lub najlepszego dostępnego
                    self.__logger.info("Szukam najlepszego portu SPID...")
                    port = get_best_spid_port()
                    self.__logger.info(f"Wybrany port: {port}")

                self.__logger.info(f"Łączę z portem {port}...")
                antenna_controller = AntennaControllerFactory.create_spid_controller(
                    port=port,
                    baudrate=config.baudrate,
                    motor_config=MotorConfig()
                )
                current_port = port

            # Inicjalizuj kontroler
            antenna_controller.initialize()

            self.__logger.info("Połączenie nawiązane pomyślnie")
            return {"status": "connected", "port": current_port, "simulator": config.use_simulator}

        except Exception as e:
            self.__logger.error(f"Błąd połączenia: {e}")
            raise HTTPException(status_code=500, detail=f"Błąd połączenia: {str(e)}")


    def disconnect_antenna(self):
        """Rozłącz z anteną"""
        global antenna_controller, current_port

        try:
            if antenna_controller:
                antenna_controller.stop()
                antenna_controller.shutdown()
                antenna_controller = None
                current_port = None

            self.__logger.info("Rozłączono z anteną")
            return {"status": "disconnected"}

        except Exception as e:
            self.__logger.error(f"Błąd rozłączania: {e}")
            raise HTTPException(status_code=500, detail=f"Błąd rozłączania: {str(e)}")

    def get_position(self):
        """Pobierz aktualną pozycję anteny (skalibrowaną)"""
        controller = get_antenna_controller()

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
        controller = get_antenna_controller()

        try:
            target_pos = Position(position.azimuth, position.elevation)
            controller.move_to(target_pos)

            return {"status": "moving", "target": position.model_dump()}

        except Exception as e:
            self.__logger.error(f"Błąd ustawiania pozycji: {e}")
            raise HTTPException(status_code=500, detail=f"Błąd ustawiania pozycji: {str(e)}")


    def stop_antenna(self):
        """Natychmiastowe zatrzymanie anteny"""
        controller = get_antenna_controller()

        try:
            controller.stop()
            self.__logger.info("Antena zatrzymana")
            return {"status": "stopped"}

        except Exception as e:
            self.__logger.error(f"Błąd zatrzymywania: {e}")
            raise HTTPException(status_code=500, detail=f"Błąd zatrzymywania: {str(e)}")


    def set_observer_location(self, location: ObserverLocationModel):
        """Ustaw lokalizację obserwatora dla obliczeń astronomicznych"""
        global astro_calculator, current_observer_location, astro_tracker

        try:
            current_observer_location = ObserverLocation(
                latitude=location.latitude,
                longitude=location.longitude,
                elevation=location.elevation,
                name=location.name
            )

            astro_calculator = AstronomicalCalculator(current_observer_location)
            astro_tracker = AstronomicalTracker(astro_calculator)

            self.__logger.info(f"Ustawiono lokalizację obserwatora: {location.name}")
            return {"status": "set", "location": location.model_dump()}

        except Exception as e:
            self.__logger.error(f"Błąd ustawiania lokalizacji: {e}")
            raise HTTPException(status_code=500, detail=f"Błąd ustawiania lokalizacji: {str(e)}")


    def get_observer_location(self):
        """Pobierz aktualną lokalizację obserwatora"""
        global current_observer_location

        if current_observer_location is None:
            raise HTTPException(status_code=404, detail="Lokalizacja obserwatora nie jest ustawiona")

        return ObserverLocationModel(
            latitude=current_observer_location.latitude,
            longitude=current_observer_location.longitude,
            elevation=current_observer_location.elevation,
            name=current_observer_location.name
        )

    def track_object(self, object_name: str, object_type: AstronomicalObjectType = AstronomicalObjectType.SUN):
        """Rozpocznij śledzenie obiektu astronomicznego"""
        controller = get_antenna_controller()
        calculator = get_astro_calculator()

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
        global tracking_active, tracking_task

        if tracking_active:
            raise HTTPException(status_code=400, detail="Śledzenie już jest aktywne. Zatrzymaj je najpierw.")

        try:
            # Sprawdź dostępność wymaganych komponentów
            get_antenna_controller()
            get_astro_tracker()

            tracking_active = True
            tracking_task = asyncio.create_task(continuous_tracking_task(config))

            self.__logger.info(f"Rozpoczęto ciągłe śledzenie obiektu: {config.object_name}")
            return {
                "status": "tracking_started",
                "object": config.object_name,
                "type": config.object_type.value,
                "config": config.model_dump()
            }

        except Exception as e:
            tracking_active = False
            self.__logger.error(f"Błąd rozpoczęcia śledzenia: {e}")
            raise HTTPException(status_code=500, detail=f"Błąd rozpoczęcia śledzenia: {str(e)}")


    def stop_tracking(self):
        """Zatrzymaj śledzenie obiektu"""
        global tracking_active, tracking_task

        try:
            if tracking_active:
                tracking_active = False
                if tracking_task and not tracking_task.done():
                    tracking_task.cancel()
                    try:
                        await tracking_task
                    except asyncio.CancelledError:
                        pass
                tracking_task = None

            # Zatrzymaj też antenę
            controller = get_antenna_controller()
            controller.stop()

            self.__logger.info("Zatrzymano śledzenie")
            return {"status": "tracking_stopped"}

        except Exception as e:
            self.__logger.error(f"Błąd zatrzymywania śledzenia: {e}")
            raise HTTPException(status_code=500, detail=f"Błąd zatrzymywania śledzenia: {str(e)}")


    def get_tracking_status(self):
        """Pobierz aktualny status śledzenia"""
        return {
            "tracking_active": tracking_active,
            "task_running": tracking_task is not None and not tracking_task.done() if tracking_task else False
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
            from antenna_controller import test_spid_connection

            # Test rotctl
            rotctl_available = sprawdz_rotctl()

            # Test połączenia ze SPID
            spid_connected = test_spid_connection(DEFAULT_SPID_PORT, DEFAULT_BAUDRATE)

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
        calculator = get_astro_calculator()

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
        controller = get_antenna_controller()

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
        controller = get_antenna_controller()

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
        controller = get_antenna_controller()

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
        controller = get_antenna_controller()

        try:
            controller.reset_calibration(save_to_file=True)
            self.__logger.info("Kalibracja została zresetowana do wartości domyślnych")
            return {"status": "reset", "message": "Kalibracja zresetowana do wartości domyślnych"}

        except Exception as e:
            self.__logger.error(f"Błąd resetowania kalibracji: {e}")
            raise HTTPException(status_code=500, detail=f"Błąd resetowania kalibracji: {str(e)}")


    def move_axis(self, move: AxisMoveModel):
        """Porusz anteną w określonej osi o zadaną wartość"""
        controller = get_antenna_controller()

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
