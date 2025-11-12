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
            success_msg = _("bias.tee.get.success.message")
            return JSONResponse(status_code=200, content={"message": f"{success_msg} {self.__biasTee.getStatus()}"})
        except Exception as ex:
            error_msg = _("bias.tee.get.error.message")
            return JSONResponse(status_code=410, content={"message": f"{error_msg}: {ex}"})

    def bias_tee_control(self, action):
        _ = self.__languageHelper.getTranslatedMessage("SDR")
        try:
            self.__biasTee.controlBiasTee(action)
            success_msg = _("bias.tee.set.success.message")
            return JSONResponse(status_code=200, content={"message": f"{success_msg} {self.__biasTee.getStatus()}"})
        except ValueError as ex:
            return JSONResponse(status_code=410, content={"message": f"{str(ex)}"})
        except Exception as ex:
            error_msg = _("bias.tee.set.error.message")
            return JSONResponse(status_code=500, content={"message": f"{error_msg}: {ex}"})

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
            error_msg = _("sdr.scan.value.error.message")
            return JSONResponse(status_code=410, content={"message": f"{error_msg}: {ex}"})
        except Exception as ex:
            error_msg = _("sdr.scan.unexpected.error.message")
            return JSONResponse(status_code=500, content={"message": f"{error_msg}: {str(ex)}"})

    def send_spectrum(self, center_freq, tone_freq, duration, sample_rate, gain):
        _ = self.__languageHelper.getTranslatedMessage("SDR")
        try:
            spectrumSender = SpectrumSender(self.__sdr, self.__languageHelper, center_freq,
                                            tone_freq, duration, sample_rate, gain)
            self.__logger.info("Starting sending signal...")
            spectrumSender.send()
            self.__logger.info("Ending sending signal...")
            
            success_msg = _("sdr.scan.success.message")
            return JSONResponse(status_code=200, content={"message": success_msg})

        except (TypeError, ValueError) as ex:
            error_msg = _("sdr.send.value.error.message")
            return JSONResponse(status_code=410, content={"message": f"{error_msg}: {ex}"})

        except Exception as ex:
            error_msg = _("sdr.send.unexpected.error.message")
            return JSONResponse(status_code=500, content={"message": f"{error_msg}: {str(ex)}"})