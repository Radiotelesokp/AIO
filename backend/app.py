import sys
import SoapySDR
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from Engine.Antenna.Model import *
from Engine.AstronomyCalculator import AstronomicalObjectType
from Engine.EngineServiceRest import EngineServiceRest
from SDR import SDRService
from LanguageHelper import LanguageHelper

SoapySDR.setLogLevel(SoapySDR.SOAPY_SDR_FATAL)
app = FastAPI(title="KN Spectrum - Project Radiotelescope")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

languageHelper = LanguageHelper(language="pl", defaultLanguage="en")
sdr = None
sdrService = None
engineService = EngineServiceRest(languageHelper)


# Bias Tee endpoints - please don't use that, because we don't have BiasTee in our hardware project
@app.get('/biastee/status')
async def bias_tee_status():
    return sdrService.bias_tee_status()

@app.put('/biastee/{action}')
async def bias_tee_control(action):
    return sdrService.bias_tee_control(action)


# SDR endpoints
@app.post('/scan/{start_freq}/{stop_freq}/{step_freq}/{sample_rate}/{gain}/{n_samples}/{channel}')
async def scan_spectrum(start_freq, stop_freq, step_freq, sample_rate, gain, n_samples, channel):
    return sdrService.scan_spectrum(start_freq, stop_freq, step_freq, sample_rate, gain, n_samples, channel)

@app.post('/send/{center_freq}/{tone_freq}/{duration}/{sample_rate}/{gain}')
async def send_spectrum(center_freq, tone_freq, duration, sample_rate, gain):
    return sdrService.send_spectrum(center_freq, tone_freq, duration, sample_rate, gain)


# Motor and antenna endpoints
@app.get("/status", response_model=StatusResponse, summary="Status systemu")
async def get_status():
    return engineService.get_status()

@app.post("/connect", summary="Połącz z anteną")
async def connect_antenna(config: ConnectionConfigModel):
    return engineService.connect_antenna(config)

@app.post("/disconnect", summary="Rozłącz z anteną")
async def disconnect_antenna():
    return engineService.disconnect_antenna()

@app.get("/position", response_model=PositionModel, summary="Aktualna pozycja")
async def get_position():
    return engineService.get_position()

@app.post("/position", summary="Ustaw pozycję")
async def set_position(position: PositionModel):
    return engineService.set_position(position)

@app.post("/stop", summary="Zatrzymaj antenę")
async def stop_antenna():
    return engineService.stop_antenna()

@app.post("/observer", summary="Ustaw lokalizację obserwatora")
async def set_observer_location(location: ObserverLocationModel):
    return engineService.set_observer_location(location)

@app.get("/observer", response_model=ObserverLocationModel, summary="Pobierz lokalizację obserwatora")
async def get_observer_location():
    return engineService.get_observer_location()

@app.post("/track/{object_name}", summary="Śledź obiekt astronomiczny")
async def track_object(object_name: str, object_type: AstronomicalObjectType = AstronomicalObjectType.SUN):
    return engineService.track_object(object_name, object_type)

@app.post("/start_tracking", summary="Rozpocznij ciągłe śledzenie obiektu")
async def start_tracking(config: TrackingConfigModel):
    return engineService.start_tracking(config)

@app.post("/stop_tracking", summary="Zatrzymaj śledzenie")
async def stop_tracking():
    return engineService.stop_tracking()

@app.get("/tracking_status", summary="Status śledzenia")
async def get_tracking_status():
    return engineService.get_tracking_status()

@app.get("/ports", summary="Lista dostępnych portów")
async def list_ports():
    return engineService.list_ports()

@app.get("/diagnostic", summary="Diagnostyka połączenia")
async def diagnostic():
    return engineService.diagnostic()

@app.get("/astronomical/position/{object_name}", summary="Pozycja obiektu astronomicznego")
async def get_astronomical_position(object_name: str):
    return engineService.get_astronomical_position(object_name)

@app.post("/calibrate_azimuth", summary="Kalibracja referencji azymutu")
async def calibrate_azimuth_reference(calibration: AzimuthCalibrationModel):
    return engineService.calibrate_azimuth_reference(calibration)

@app.get("/calibration", summary="Pobierz aktualną kalibrację")
async def get_calibration():
    return engineService.get_calibration()

@app.post("/calibration", summary="Ustaw kalibrację")
async def set_calibration(calibration: CalibrationModel):
    return engineService.set_calibration(calibration)

@app.post("/reset_calibration", summary="Resetuj kalibrację")
async def reset_calibration():
    return engineService.reset_calibration()

@app.post("/move_axis", summary="Ruch w osi")
async def move_axis(move: AxisMoveModel):
    return engineService.move_axis(move)

@app.post("/emergency_stop/{port}/{speed}", summary="Zatrzymanie dotychczasowych działań i powrót do bezpiecznej pozycji")
async def move_axis(port, speed):
    return engineService.emergency_stop(port, speed)


if __name__ == '__main__':
    try:
        args = dict(driver="hackrf", serial="0000000000000000436c63dc2f272b63")
        sdr = SoapySDR.Device(args)
        driver = sdr.getDriverKey().lower()
        logger.info(f"Used driver SDR: {driver}")

        if driver != "hackrf":
            raise ValueError(f"No SDR supported - required 'hackrf', but is {driver}")

        sdrService = SDRService(sdr = sdr, languageHelper=languageHelper)

    except Exception as ex:
        sys.exit(f"Connection error with SDR: {ex}")

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)