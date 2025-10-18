import base64
import logging
import SoapySDR
from fastapi.responses import JSONResponse
from backend.SDR import SpectrumSender, BiasTee, SpectrumScanner


class SDRService:
    __logger = logging.getLogger(__name__)
    __biasTee :BiasTee
    __sdr: SoapySDR

    def __init__(self, sdr: SoapySDR):
        self.__biasTee = BiasTee(sdr = sdr)
        self.__sdr = sdr

    def bias_tee_status(self):
        try:
            return JSONResponse(status_code=200, content={"message": f"Bias-Tee status: {self.__biasTee.getStatus()}"})
        except Exception as ex:
            return JSONResponse(status_code=410, content={"message": f"Bias-Tee get status error: {ex}"})

    def bias_tee_control(self, action):
        try:
            self.__biasTee.controlBiasTee(action)
            return JSONResponse(status_code=200, content={"message": f"Bias-Tee status set on: {self.__biasTee.getStatus()}"})
        except ValueError as ex:
            return JSONResponse(status_code=410, content={"message": f"{str(ex)}"})
        except Exception as ex:
            return JSONResponse(status_code=500, content={"message": f"Bias-Tee set status error: {ex}"})

    def scan_spectrum(self, start_freq, stop_freq, step_freq, sample_rate, gain, n_samples, channel):
        try:
            spectrumScanner = SpectrumScanner(self.__sdr, start_freq, stop_freq, step_freq, sample_rate, gain, n_samples, channel)
            self.__logger.info("Starting spectrum scan. Please wait...")
            result, zipfile = spectrumScanner.scan()
            self.__logger.info("Success spectrum scan.")
            zip_base64 = base64.b64encode(zipfile.read()).decode('utf-8')

            return JSONResponse(status_code=200, content={"message": f"Data: {result}",
                                                          "filename": "spectrum_file.zip",
                                                          "zip_base64": zip_base64})

        except (TypeError, ValueError) as ex:
            return JSONResponse(status_code=410, content={"message": f"Please give correct parameters. Error: {ex}"})
        except Exception as ex:
            return JSONResponse(status_code=500, content={"message": f"SDR have some problems during receive signal: {str(ex)}"})

    def send_spectrum(self, center_freq, tone_freq, duration, sample_rate, gain):
        try:
            spectrumSender = SpectrumSender(self.__sdr, center_freq, tone_freq, duration, sample_rate, gain)
            self.__logger.info("Starting sending signal...")
            spectrumSender.send()
            self.__logger.info("Ending sending signal...")

            return JSONResponse(status_code=200, content={f"Send signal successfully."})

        except (TypeError, ValueError) as ex:
            return JSONResponse(status_code=410, content={"message": f"Please give correct parameters. Error: {ex}"})

        except Exception as ex:
            return JSONResponse(status_code=500, content={"message": f"SDR have some problems during send signal: {str(ex)}"})