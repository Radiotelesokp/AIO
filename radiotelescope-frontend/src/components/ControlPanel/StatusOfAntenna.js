import { useEffect, useState, useCallback } from "react";
import "./StatusOfAntenna.scss";

const API_BASE = process.env.REACT_APP_API_URL || "http://localhost:8000";

export default function StatusOfAntenna({ log, updateControlsState }) {
  const [isConnected, setIsConnected] = useState(false);
  const [azimuth, setAzimuth] = useState(null);
  const [elevation, setElevation] = useState(null);
  const [isMoving, setIsMoving] = useState(false);
  const [port, setPort] = useState("---");
  const [time, setTime] = useState("--:--:--");

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
      if (!response.ok)
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);

      return await response.json();
    } catch (error) {
      if (log) log(`Błąd API: ${error.message}`, "error");
      throw error;
    }
  }, [log]);

  const updateConnectionStatus = useCallback(() => {
    if (updateControlsState) updateControlsState();
  }, [updateControlsState]);

  const updateStatus = useCallback(async () => {
    try {
      const status = await apiCall("/status", "GET");

      setIsConnected(status.connected);
      updateConnectionStatus();

      if (status.current_position) {
        setAzimuth(status.current_position.azimuth.toFixed(1));
        setElevation(status.current_position.elevation.toFixed(1));
      } else {
        setAzimuth(null);
        setElevation(null);
      }

      setIsMoving(status.is_moving);
      setPort(status.port || "---");
    } catch {
      // Error already logged in apiCall
    }
  }, [apiCall, updateConnectionStatus]);

  useEffect(() => {
    const timer = setInterval(() => {
      setTime(new Date().toLocaleTimeString());
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    updateStatus();
    const interval = setInterval(updateStatus, 5000); // update every 5s
    return () => clearInterval(interval);
  }, [updateStatus]);

  const emergencyStop = async () => {
    if (log) log("ZATRZYMANIE AWARYJNE!", "warning");
    try {
      await apiCall("/stop", "POST");
    } catch (error) {
      if (log) log(`Błąd zatrzymania: ${error.message}`, "error");
    }
  };

  return (
    <div className="status-sidebar" id="statusSidebar">
      <div className="status-content">

        <div className={`status-item ${isConnected ? "connected" : "disconnected"}`}>
          <div className="status-label">Połączenie</div>
          <div className="status-value">{isConnected ? "Połączony" : "Rozłączony"}</div>
        </div>

        <div className="status-item">
          <div className="status-label">Port</div>
          <div className="status-value">{port}</div>
        </div>

        <div className="status-item">
          <div className="status-label">Azymut</div>
          <div className="status-value">{azimuth !== null ? `${azimuth}°` : "---°"}</div>
        </div>

        <div className="status-item">
          <div className="status-label">Elewacja</div>
          <div className="status-value">{elevation !== null ? `${elevation}°` : "---°"}</div>
        </div>

        <div className="status-item">
          <div className="status-label">Stan</div>
          <div className="status-value">{isMoving ? "W ruchu" : "Zatrzymany"}</div>
        </div>

        <div className="status-item">
          <div className="status-label">Czas</div>
          <div className="status-value">{time}</div>
        </div>

        <button className="emergency-stop" onClick={emergencyStop}>STOP AWARYJNY</button>
      </div>
    </div>
  );
}