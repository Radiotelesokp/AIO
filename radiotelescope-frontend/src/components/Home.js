import { useEffect, useState } from "react";
import "./styles/Home.scss";

export default function Home() {
  const [observation, setObservation] = useState({
    target: "Pulsar PSR B0329+54",
    date: "2025-10-21 22:43",
    operator: "Jan Kowalski",
  });

  const [status, setStatus] = useState({
    Silniki: "OK",
    SDR: "OK",
    Czujnik_zalania: "OK",
    Reset: "ERROR",
  });

  useEffect(() => {
    const interval = setInterval(() => {
      const keys = Object.keys(status);
      const randomKey = keys[Math.floor(Math.random() * keys.length)];
      setStatus((prev) => ({
        ...prev,
        [randomKey]: Math.random() > 0.9 ? "ERROR" : "OK",
      }));
    }, 5000);
    return () => clearInterval(interval);
  }, [status]);

  return (
    <div className="container">
      <h2>Panel główny radioteleskopu</h2>

      <section>
        <h3>Ostatnia obserwacja</h3>
        <div className="card">
          <p><strong>Obiekt:</strong> {observation.target}</p>
          <p><strong>Data:</strong> {observation.date}</p>
          <p><strong>Operator:</strong> {observation.operator}</p>
        </div>
      </section>

      <section>
        <h3>Status systemu</h3>
        <div className="status-grid">
          {Object.entries(status).map(([key, value]) => (
            <div
              key={key}
              className={`status-item ${value === "OK" ? "ok" : "error"}`}
            >
              <p className="status-name">{key}</p>
              <strong className="status-value">{value}</strong>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
