import io
import zipfile
import numpy as np
import SoapySDR
import logging
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
import os


class SpectrumScanner:
    logger = logging.getLogger(__name__)

    def __init__(self, sdr, start_freq, stop_freq, step_freq, sample_rate, gain, n_samples, channel):
        self.sdr = sdr
        self.start_freq = self.__convertStrToFloat(start_freq)
        self.stop_freq = self.__convertStrToFloat(stop_freq)
        self.step_freq = self.__convertStrToFloat(step_freq)
        self.sample_rate = self.__convertStrToFloat(sample_rate)
        self.gain = self.__convertStrToFloat(gain)
        self.n_samples = self.__convertStrToInt(n_samples)
        self.channel = self.__convertStrToInt(channel)

    def __convertStrToFloat(self, variable: str) -> float:
        try:
            return float(variable)
        except (TypeError, ValueError) as e:
            self.logger.warning(f"Conversion to float failed for value: {variable} ({e})")
            raise ValueError(f"Conversion to float failed for value: {variable} ({e})")

    def __convertStrToInt(self, variable: str) -> int:
        try:
            return int(variable)
        except (TypeError, ValueError) as e:
            self.logger.warning(f"Conversion to int failed for value: {variable} ({e})")
            raise ValueError(f"Conversion to int failed for value: {variable} ({e})")

    # Scan one frequency of spectrum
    def __getSimpleFrequency(self, freq):
        direction = SoapySDR.SOAPY_SDR_RX
        sample_format = SoapySDR.SOAPY_SDR_CF32

        self.sdr.setSampleRate(direction, self.channel, self.sample_rate)
        self.sdr.setFrequency(direction, self.channel, freq)
        self.sdr.setGain(direction, self.channel, self.gain)

        buffer = np.empty(self.n_samples, dtype=np.complex64)
        stream = self.sdr.setupStream(direction, sample_format)
        self.sdr.activateStream(stream)
        result = self.sdr.readStream(stream, [buffer], self.n_samples)

        self.sdr.deactivateStream(stream)
        self.sdr.closeStream(stream)

        if result.ret <= 0:
            self.logger.warning(f"SDR sampling error: Cannot read {freq} Hz. ({result.ret})")

        return buffer[:result.ret]

    def scan(self):
        results = []
        today_str = datetime.now().isoformat(sep="T", timespec="seconds")
        max_filename = f"max_{int(self.start_freq)}-{int(self.stop_freq)}_{today_str}.csv"
        mean_filename = f"mean_{int(self.start_freq)}-{int(self.stop_freq)}_{today_str}.csv"

        with open(max_filename, "w") as max_file, open(mean_filename, "w") as mean_file:
            self.logger.info(f"Write to files: {max_filename}, {mean_filename}")
            max_file.write("frequency_hz,max_db\n")
            mean_file.write("frequency_hz,mean_db\n")

            for freq in np.arange(self.start_freq, self.stop_freq + self.step_freq, self.step_freq):
                samples = self.__getSimpleFrequency(freq)
                window = np.hamming(len(samples)) # Hamming window
                samples_windowed = samples * window

                spectrum = np.fft.fftshift(np.fft.fft(samples_windowed))

                max_val = np.abs(spectrum).max()            # wzor na max widma:   20*log10(max(|FFT(samples)|))
                mean_val = np.mean(np.abs(spectrum) ** 2)   # wzor na srednia moc: 10*log10(mean(|FFT(samples)|^2))

                if max_val == 0 or mean_val == 0:
                    self.logger.warning(f"Ignore {int(freq)} Hz - no signal")
                    continue

                max_db = 20 * np.log10(max_val)
                mean_db = 10 * np.log10(mean_val)

                results.append((freq, max_db, mean_db))
                max_file.write(f"{int(freq)},{max_db:.2f}\n")
                mean_file.write(f"{int(freq)},{mean_db:.2f}\n")

        self.__plot_max_and_mean(f"{int(self.start_freq)}-{int(self.stop_freq)}_{today_str}")

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
            zip_file.write(f"max_{int(self.start_freq)}-{int(self.stop_freq)}_{today_str}.csv")
            zip_file.write(f"mean_{int(self.start_freq)}-{int(self.stop_freq)}_{today_str}.csv")
            zip_file.write(f"spectrum_{int(self.start_freq)}-{int(self.stop_freq)}_{today_str}.png")
        zip_buffer.seek(0)

        return results, zip_buffer

    def __plot_max_and_mean(self, prefix):
        max_file = f"max_{prefix}.csv"
        mean_file = f"mean_{prefix}.csv"

        if not os.path.exists(max_file) or not os.path.exists(mean_file):
            raise ValueError(f"{max_file} or {mean_file} does not exist")

        df_max = pd.read_csv(max_file)
        df_mean = pd.read_csv(mean_file)

        plt.figure(figsize=(10, 5))
        plt.plot(df_max["frequency_hz"], df_max["max_db"], label="Max dB", marker='o')
        plt.plot(df_mean["frequency_hz"], df_mean["mean_db"], label="Mean dB", marker='x')

        plt.title(f"Widmo sygnalu - {prefix}")
        plt.xlabel("Czestotliwosc [Hz]")
        plt.ylabel("Poziom [dB]")
        plt.legend()
        plt.grid(True)
        plt.tight_layout()

        png_file = f"spectrum_{prefix}.png"
        plt.savefig(png_file)
        plt.close()
        self.logger.info(f"Spectrum plot saved to {png_file}")