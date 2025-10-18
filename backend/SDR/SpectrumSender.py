import SoapySDR
import logging
import numpy as np


class SpectrumSender:
    logger = logging.getLogger(__name__)

    def __init__(self, sdr, center_freq, tone_freq, duration, sample_rate, gain):
        self.sdr = sdr
        self.center_freq = self.__convertStrToFloat(center_freq)
        self.gain = self.__convertStrToFloat(gain)
        self.duration = self.__convertStrToFloat(duration)
        self.sample_rate = self.__convertStrToFloat(sample_rate)
        self.tone_freq = self.__convertStrToFloat(tone_freq)


    def __convertStrToFloat(self, variable: str) -> float:
        try:
            return float(variable)
        except (TypeError, ValueError) as e:
            self.logger.warning(f"Conversion to float failed for value: {variable} ({e})")
            raise ValueError(f"Conversion to float failed for value: {variable} ({e})")

    def send(self):
        self.sdr.setSampleRate(SoapySDR.SOAPY_SDR_TX, 0, self.sample_rate)
        self.sdr.setFrequency(SoapySDR.SOAPY_SDR_TX, 0, self.center_freq)
        self.sdr.setGain(SoapySDR.SOAPY_SDR_TX, 0, self.gain)

        txStream = self.sdr.setupStream(SoapySDR.SOAPY_SDR_TX, SoapySDR.SOAPY_SDR_CF32)
        self.sdr.activateStream(txStream)

        num_samples = int(self.sample_rate * self.duration)
        t = np.arange(num_samples) / self.sample_rate
        iq = np.exp(2j * np.pi * self.tone_freq * t).astype(np.complex64)

        chunk_size = 8192
        for i in range(0, len(iq), chunk_size):
            buff = iq[i:i + chunk_size]
            sr = self.sdr.writeStream(txStream, [buff], len(buff))
            if sr.ret != len(buff):
                self.logger.warning("Warning: underflow", sr)

        self.sdr.deactivateStream(txStream)
        self.sdr.closeStream(txStream)