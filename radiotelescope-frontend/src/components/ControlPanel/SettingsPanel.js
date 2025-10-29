import React, { useState, useCallback } from "react";
import "./SettingsPanel.scss";

export default function SettingsPanel({ log }) {
  const API_BASE = "http://localhost:8000";
  const [port, setPort] = useState("");
  const [simulatorMode, setSimulatorMode] = useState(false);
  const [azimuth, setAzimuth] = useState(0);
  const [elevation, setElevation] = useState(0);
  const [stepSize, setStepSize] = useState(1.0);
  const [selectedObject, setSelectedObject] = useState("");
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [location, setLocation] = useState({
    latitude: 52.4064,
    longitude: 16.9252,
    elevation: 75,
    name: "Poznań",
  });
  const [activeTab, setActiveTab] = useState("Antenna");
  const [startFreq, setStartFreq] = useState(1000.0);
  const [stopFreq, setStopFreq] = useState(10000.0);
  const [stepFreq, setStepFreq] = useState(100.0);
  const [sampleRate, setSampleRate] = useState(5.0);
  const [gain, setGain] = useState(5.0);
  const [nSamples, setNSamples] = useState(50);
  const [channel, setChannel] = useState(0);
  const [biasAction, setBiasAction] = useState("off");

  const [centerFreq, setCenterFreq] = useState(10000.0);
  const [toneFreq, setToneFreq] = useState(1000.0);
  const [duration, setDuration] = useState(100.0);
  const [sampleRateSend, setSampleRateSend] = useState(5.0);
  const [gainSend, setGainSend] = useState(5.0);

  const apiCall = useCallback(async (endpoint, method = "GET", data = null) => {
      try {
        const config = {
          method,
           headers: {
              "Content-Type": "application/json",
              "Accept-Language": "pl",
            },
        };
  
        if (data) config.body = JSON.stringify(data);
  
        const response = await fetch(API_BASE + endpoint, config);
        const message = response.json();
        console.log(message);
        console.log(response);
        if (!response.ok)
          throw new Error(`HTTP ${response.status}: ${message.message}`);
  
        return await response.json();
      } catch (error) {
        if (log) log(`Błąd API: ${error.message}`, "error");
        throw error;
      }
    }, [log]);

  const connectAntenna = async () => {
    try {
      await apiCall("/connect", "POST", { port, simulatorMode });
      log(`Połączono z anteną.`, "info");
    } catch (err) {
      if (log) log(`Błąd połączenia: ${err.message}`, "error");
    }
  };

  const disconnectAntenna = async () => {
  try {
    await apiCall("/disconnect", "POST");
    log("Rozłączono.", "info");
  } catch (err) {
    log(`Błąd rozłączenia: ${err.message}`, "error");
  }
};

const moveToPosition = async () => {
  try {
    await apiCall("/move", "POST", { azimuth, elevation });
    log("Ustawiono pozycję.", "info");
  } catch (err) {
    log(`Błąd ruchu: ${err.message}`, "error");
  }
};

const stopAntenna = async () => {
  try {
    await apiCall("/stop", "POST");
    log("Zatrzymano antenę.", "info");
  } catch (err) {
    log(`Błąd zatrzymania: ${err.message}`, "error");
  }
};

const singleAxisMove = async (axis, direction) => {
  try {
    await apiCall("/move/single", "POST", { axis, direction, step: stepSize });
    log(`Ruch osi ${axis} (${direction})`, "info");
  } catch (err) {
    log(`Błąd sterowania osi: ${err.message}`, "error");
  }
};

const selectAstronomicalObject = (name, type) => {
  setSelectedObject(name);
  log(`Wybrano obiekt astronomiczny: ${name} (${type})`, "info");
};

const startTracking = async () => {
  try {
    await apiCall("/tracking/start", "POST", { object: selectedObject });
    log("Śledzenie rozpoczęte.", "info");
  } catch (err) {
    log(`Błąd śledzenia: ${err.message}`, "error");
  }
};

const stopTracking = async () => {
  try {
    await apiCall("/tracking/stop", "POST");
    log("Śledzenie zatrzymane.", "info");
  } catch (err) {
    log(`Błąd zatrzymania: ${err.message}`, "error");
  }
};

const getObjectPosition = async () => {
  try {
    const pos = await apiCall("/object/position", "GET");
    log(`Pozycja obiektu: Az=${pos.azimuth}°, El=${pos.elevation}°`, "info");
  } catch (err) {
    log(`Błąd odczytu pozycji obiektu: ${err.message}`, "error");
  }
};

const moveToObject = async () => {
  try {
    await apiCall("/object/move", "POST", { object: selectedObject });
    log("Przesuwanie do obiektu...", "info");
  } catch (err) {
    log(`Błąd przesuwania: ${err.message}`, "error");
  }
};

const setPresetPosition = (az, el) => {
  setAzimuth(az);
  setElevation(el);
  log(`Ustawiono pozycję preset: Az=${az}, El=${el}`, "info");
};

const moveToPresetPosition = async () => {
  await moveToPosition();
};

const calibrateNorth = async () => {
  try {
    await apiCall("/calibrate/north", "POST");
    log("Kalibracja północy zakończona.", "info");
  } catch (err) {
    log(`Błąd kalibracji: ${err.message}`, "error");
  }
};

const resetCalibration = async () => {
  try {
    await apiCall("/calibrate/reset", "POST");
    log("Kalibracja zresetowana.", "info");
  } catch (err) {
    log(`Błąd resetowania: ${err.message}`, "error");
  }
};

const getSignal = async () => {
  try {
    await apiCall(`scan/${startFreq}/${stopFreq}/${stepFreq}/${sampleRate}/${gain}/${nSamples}/${channel}`, "POST");
    log("Rozpoczęto proces zbierania danych.", "info");
  } catch (err) {
    log(`Błąd podczas zbierania danych: ${err.message}`, "error");
  }
};

const sendSignal = async () => {
  try {
    await apiCall(`send/${centerFreq}/${toneFreq}/${duration}/${sampleRateSend}/${gainSend}`, "POST");
    log("Rozpoczęto nadawanie sygnału.", "info");
  } catch (err) {
    log(`Błąd nadawania: ${err.message}`, "error");
  }
};

const applyAxisSettings = async () => {
  log("Ustawienia osi zapisane (mock).", "info");
};

const applyOffsets = async () => {
  log("Offset kalibracji zastosowany (mock).", "info");
};

const setObserverLocation = async () => {
  log(`Ustawiono lokalizację: ${location.name}`, "info");
};

const getObserverLocation = async () => {
  log(`Aktualna lokalizacja: ${location.name}`, "info");
};


  return (
    <div className="settings-container">
      <div className="tabs">
        {["Antenna", "SDR"].map((tab) => (<button key={tab} className="tab" style={{ color: activeTab === tab ? "red" : undefined }}
        onClick={() => setActiveTab(tab) }>{tab}</button>))}
      </div>

      {activeTab === "Antenna" && (
        <div className="settings-section">
          <div className="card">
            <h3>Połączenie</h3>
            <div className="control-group">
              <label>Port szeregowy:</label>
              <div className="input-group">
                <select value={port} onChange={(e) => setPort(e.target.value)}>
                  <option value="">Auto-detect</option>
                  <option value="/dev/tty.usbserial-A10PDNT7">/dev/tty.usbserial-A10PDNT7</option>
                  <option value="/dev/ttyUSB0">/dev/ttyUSB0</option>
                  <option value="COM10">COM10</option>
                </select>
                <button className="button-refresh">Odśwież</button>
              </div>
            </div>

            <div className="control-group checkbox">
              <label>
                <input type="checkbox" checked={simulatorMode} onChange={(e) => setSimulatorMode(e.target.checked)} /> 
                Tryb symulatora 
              </label>
            </div>

            <div className="button-group">
              <button onClick={connectAntenna}>Połącz</button>
              <button onClick={disconnectAntenna}>Rozłącz</button>
            </div>
          </div>

          <div className="card">
            <h3>Sterowanie Pozycją</h3>
            <div className="control-group">
              <label>Azymut (0–360°):</label>
              <input type="number" min="0" max="360" step="0.1" value={azimuth} onChange={(e) => setAzimuth(parseFloat(e.target.value))} />
            </div>

            <div className="control-group">
              <label>Elewacja (0–90°):</label>
              <input type="number" min="0" max="90" step="0.1" value={elevation} onChange={(e) => setElevation(parseFloat(e.target.value))} />
            </div>

            <div className="button-group">
              <button onClick={moveToPosition}>Ustaw Pozycję</button>
              <button onClick={stopAntenna}>Stop</button>
            </div>
          </div>

          <div className="card">
            <h3>Sterowanie Ręczne</h3>
            <div className="manual-control">
              <div className="axis-control">
                <h4>Azymut</h4>
                <div className="axis-buttons">
                  <button onClick={() => singleAxisMove("azimuth", "negative")}>◄</button>
                  <span>Az</span>
                  <button onClick={() => singleAxisMove("azimuth", "positive")}>►</button>
                </div>
              </div>
              <div className="axis-control">
                <h4>Elewacja</h4>
                <div className="axis-buttons">
                  <button onClick={() => singleAxisMove("elevation", "positive")}>▼</button>
                  <span>El</span>
                  <button onClick={() => singleAxisMove("elevation", "negative")}>▲</button>
                </div>
              </div>
            </div>
            <div className="control-group">
              <label>Wielkość kroku (°):</label>
              <input type="number" min="0.1" max="10" step="0.1" value={stepSize} onChange={(e) => setStepSize(parseFloat(e.target.value))} />
            </div>
          </div>

          <div className="card">
            <h3>Śledzenie Astronomiczne</h3>

            <div className="control-group">
              <label>Wybierz obiekt:</label>
              <div className="astronomical-objects">
                {["Słońce", "Księżyc", "Merkury", "Wenus", "Mars", "Jowisz", "Saturn", "Uran", "Neptun"].map((obj) => (
                  <div key={obj} className={`object-button ${selectedObject === obj ? "selected" : ""}`}
                    onClick={() => selectAstronomicalObject(obj, "planet")}> {obj} </div>
                ))}
              </div>
            </div>

            <div className="control-group">
              <label>Wybrany obiekt:</label>
              <input type="text" readOnly value={selectedObject} placeholder="Wybierz obiekt" />
            </div>

            <div className="button-group">
              <button onClick={startTracking}>Rozpocznij Śledzenie</button>
              <button onClick={stopTracking}>Zatrzymaj Śledzenie</button>
              <button onClick={getObjectPosition}>Pozycja Obiektu</button>
              <button onClick={moveToObject}>Przesuń do Obiektu</button>
            </div>
          </div>

          <button className="advanced-options-toggle" onClick={() => setShowAdvanced(!showAdvanced)} > 
            Opcje Zaawansowane {showAdvanced ? "▲" : "▼"} </button>

          {showAdvanced && (
            <div className="advanced-options-container">
              <div className="card">
                <h3>Zapamiętane Pozycje</h3>
                <div className="control-group">
                  <label>Szybki wybór pozycji:</label>
                  <div className="astronomical-objects">
                    <div onClick={() => setPresetPosition(0, 90)}>Zenit</div>
                    <div onClick={() => setPresetPosition(0, 10)}>Północ</div>
                    <div onClick={() => setPresetPosition(90, 10)}>Wschód</div>
                    <div onClick={() => setPresetPosition(180, 10)}>Południe</div>
                    <div onClick={() => setPresetPosition(270, 10)}>Zachód</div>
                  </div>
                </div>
                <div className="button-group">
                  <button onClick={moveToPresetPosition}>Przesuń do Pozycji</button>
                </div>
              </div>

              <div className="card">
                <h3>Kalibracja Anteny</h3>
                <div className="button-group">
                  <button onClick={calibrateNorth}>Kalibruj Północ</button>
                  <button onClick={resetCalibration}>Resetuj Kalibrację</button>
                </div>
              </div>

              <div className="card">
                <h3>Lokalizacja Obserwatora</h3>
                <div className="control-group">
                  <label>Szerokość geograficzna:</label>
                  <input type="number" value={location.latitude} onChange={(e) => setLocation({ ...location, latitude: parseFloat(e.target.value) }) }/>
                </div>
                <div className="control-group">
                  <label>Długość geograficzna:</label>
                  <input type="number" value={location.longitude} onChange={(e) => setLocation({ ...location, longitude: parseFloat(e.target.value) })}/>
                </div>
                <div className="control-group">
                  <label>Wysokość n.p.m. (m):</label>
                  <input type="number" value={location.elevation} onChange={(e) => setLocation({ ...location, elevation: parseFloat(e.target.value) })}/>
                </div>
                <div className="control-group">
                  <label>Nazwa lokalizacji:</label>
                  <input type="text" value={location.name} onChange={(e) => setLocation({ ...location, name: e.target.value }) }/>
                </div>
                <div className="button-group">
                  <button onClick={setObserverLocation}>Ustaw Lokalizację</button>
                  <button onClick={getObserverLocation}>Pobierz Lokalizację</button>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
      {activeTab === "SDR" && (
        <div className="settings-section">
          <div className="card">
            <h3>Zebranie sygnału</h3>
            <div className="control-group">
              <label>Początkowa częstotliwość (Hz):</label>
                <input type="number" value={startFreq} onChange={(e) => setStartFreq(parseFloat(e.target.value))}/>
            </div>

            <div className="control-group">
              <label>Końcowa częstotliwość (Hz):</label>
                <input type="number" value={stopFreq} onChange={(e) => setStopFreq(parseFloat(e.target.value))} />
            </div>

            <div className="control-group">
              <label>Krok częstotliwości (Hz):</label>
              <input type="number" value={stepFreq} onChange={(e) => setStepFreq(parseFloat(e.target.value))} />
            </div>

            <div className="control-group">
              <label>Częstotliwość próbkowania (Msps):</label>
              <input type="number" value={sampleRate} onChange={(e) => setSampleRate(parseFloat(e.target.value))}/>
            </div>

            <div className="control-group">
              <label>Wzmocnienie (dB):</label>
              <input type="number" value={gain} onChange={(e) => setGain(parseFloat(e.target.value))} />
            </div>

            <div className="control-group">
              <label>Liczba próbek:</label>
              <input type="number" value={nSamples} onChange={(e) => setNSamples(parseInt(e.target.value))} />
            </div>

            <div className="control-group">
              <label>Kanał:</label>
              <select value={channel} onChange={(e) => setChannel(parseInt(e.target.value))}>
                <option value={0}>Kanał 0</option>
                <option value={1}>Kanał 1</option>
              </select>
            </div>

            <div className="control-group">
              <label>Zasilanie bias tee:</label>
              <select value={biasAction} onChange={(e) => setBiasAction(e.target.value)}>
                <option value="off">Wyłącz</option>
                <option value="on">Włącz</option>
              </select>
            </div>

            <div className="button-group">
              <button onClick={getSignal}>Zbieraj sygnał</button>
            </div>
          </div>
          <div className="card">
            <h3>Wysłanie sygnału</h3>
            <div className="control-group">
              <label>Częstotliwość środkowa (Hz):</label>
              <input type="number" value={centerFreq} onChange={(e) => setCenterFreq(parseFloat(e.target.value))} />
            </div>

            <div className="control-group">
              <label>Częstotliwość tonu (Hz):</label>
              <input type="number" value={toneFreq} onChange={(e) => setToneFreq(parseFloat(e.target.value))}/>
            </div>

            <div className="control-group">
              <label>Czas trwania (ms):</label>
              <input type="number" value={duration} onChange={(e) => setDuration(parseFloat(e.target.value))}/>
            </div>

            <div className="control-group">
              <label>Częstotliwość próbkowania (Msps):</label>
              <input type="number" value={sampleRateSend} onChange={(e) => setSampleRateSend(parseFloat(e.target.value))}/>
            </div>

            <div className="control-group">
              <label>Wzmocnienie (dB):</label>
              <input type="number" value={gainSend} onChange={(e) => setGainSend(parseFloat(e.target.value))}/>
            </div>

            <div className="button-group">
              <button onClick={getSignal}>Wyślij sygnał</button>
            </div>
          </div>
          
          
        </div>
          )}
    </div>
  );
}
