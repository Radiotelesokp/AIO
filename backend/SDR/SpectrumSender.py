import SoapySDR
import logging
import numpy as np


class SpectrumSender:
    __logger = logging.getLogger(__name__)

    def __init__(self, __sdr, languageHelper, center_freq, tone_freq, duration, sample_rate, gain):
        self.__sdr = __sdr
        self._ = languageHelper.getTranslatedMessage("SDR")
        self.__center_freq = self.__convertStrToFloat(center_freq)
        self.__gain = self.__convertStrToFloat(gain)
        self.__duration = self.__convertStrToFloat(duration)
        self.__sample_rate = self.__convertStrToFloat(sample_rate)
        self.__tone_freq = self.__convertStrToFloat(tone_freq)


    def __convertStrToFloat(self, variable: str) -> float:
        try:
            return float(variable)
        except (TypeError, ValueError) as e:
            self.__logger.warning(f"Conversion to float failed for value: {variable} ({e})")
            error_msg = self._("spectrum.scanner.convertion.to.float.error")
            raise ValueError(f"{error_msg}: {variable} ({e})")

    def send(self):
        self.__sdr.setSampleRate(SoapySDR.SOAPY_SDR_TX, 0, self.__sample_rate)
        self.__sdr.setFrequency(SoapySDR.SOAPY_SDR_TX, 0, self.__center_freq)
        self.__sdr.setGain(SoapySDR.SOAPY_SDR_TX, 0, self.__gain)

        txStream = self.__sdr.setupStream(SoapySDR.SOAPY_SDR_TX, SoapySDR.SOAPY_SDR_CF32)
        self.__sdr.activateStream(txStream)

        num_samples = int(self.__sample_rate * self.__duration)
        t = np.arange(num_samples) / self.__sample_rate
        iq = np.exp(2j * np.pi * self.__tone_freq * t).astype(np.complex64)

        chunk_size = 8192
        for i in range(0, len(iq), chunk_size):
            buff = iq[i:i + chunk_size]
            sr = self.__sdr.writeStream(txStream, [buff], len(buff))
            if sr.ret != len(buff):
                self.__logger.warning("Warning: underflow", sr)

        self.__sdr.deactivateStream(txStream)
        self.__sdr.closeStream(txStream)