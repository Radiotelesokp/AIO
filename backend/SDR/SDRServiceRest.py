import base64
import logging
import SoapySDR
from fastapi.responses import JSONResponse

from LanguageHelper import LanguageHelper
from .BiasTee import BiasTee
from .SpectrumScanner import SpectrumScanner
from .SpectrumSender import SpectrumSender


class SDRService:
    __logger = logging.getLogger(__name__)
    __biasTee :BiasTee
    __sdr: SoapySDR

    def __init__(self, sdr: SoapySDR, languageHelper: LanguageHelper):
        self.__biasTee = BiasTee(sdr, languageHelper)
        self.__sdr = sdr
        self.__languageHelper = languageHelper

    def bias_tee_status(self):
        _ = self.__languageHelper.getTranslatedMessage("SDR")
        try:
            return JSONResponse(status_code=200, content={"message": f"{_("bias.tee.get.success.message")}"
                                                                     f" {self.__biasTee.getStatus()}"})
        except Exception as ex:
            return JSONResponse(status_code=410, content={"message": f"{_("bias.tee.get.error.message")} {ex}"})

    def bias_tee_control(self, action):
        _ = self.__languageHelper.getTranslatedMessage("SDR")
        try:
            self.__biasTee.controlBiasTee(action)
            return JSONResponse(status_code=200, content={"message": f"{_("bias.tee.set.success.message")}"
                                                                     f" {self.__biasTee.getStatus()}"})
        except ValueError as ex:
            return JSONResponse(status_code=410, content={"message": f"{str(ex)}"})
        except Exception as ex:
            return JSONResponse(status_code=500, content={"message": f"{_("bias.tee.set.error.message")} {ex}"})

    def scan_spectrum(self, start_freq, stop_freq, step_freq, sample_rate, gain, n_samples, channel):
        _ = self.__languageHelper.getTranslatedMessage("SDR")
        try:
            spectrumScanner = SpectrumScanner(self.__sdr,self.__languageHelper, start_freq,
                                              stop_freq, step_freq, sample_rate, gain, n_samples, channel)
            self.__logger.info("Starting spectrum scan. Please wait...")
            result, zipfile = spectrumScanner.scan()
            self.__logger.info("Success spectrum scan.")
            zip_base64 = base64.b64encode(zipfile.read()).decode('utf-8')

            return JSONResponse(status_code=200, content={"message": f"Data: {result}",
                                                          "filename": "spectrum_file.zip",
                                                          "zip_base64": zip_base64})

        except (TypeError, ValueError) as ex:
            return JSONResponse(status_code=410, content={"message": f"{_("sdr.scan.value.error.message")} {ex}"})
        except Exception as ex:
            return JSONResponse(status_code=500, content={"message": f"{_("sdr.scan.unexpected.error.message")}"
                                                                     f" {str(ex)}"})

    def send_spectrum(self, center_freq, tone_freq, duration, sample_rate, gain):
        _ = self.__languageHelper.getTranslatedMessage("SDR")
        try:
            spectrumSender = SpectrumSender(self.__sdr, self.__languageHelper, center_freq,
                                            tone_freq, duration, sample_rate, gain)
            self.__logger.info("Starting sending signal...")
            spectrumSender.send()
            self.__logger.info("Ending sending signal...")

            return JSONResponse(status_code=200, content={f"{_("sdr.scan.success.message")}"})

        except (TypeError, ValueError) as ex:
            return JSONResponse(status_code=410, content={"message": f"{_("sdr.send.value.error.message")} {ex}"})

        except Exception as ex:
            return JSONResponse(status_code=500, content={"message": f"{_("sdr.send.unexpected.error.message")}"
                                                                     f" {str(ex)}"})