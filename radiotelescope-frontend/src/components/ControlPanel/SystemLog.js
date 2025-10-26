import { forwardRef, useImperativeHandle, useState, useRef, useEffect } from "react";
import "./SystemLog.scss";

const SystemLog = forwardRef(({ autoScroll = true, setAutoScroll }, ref) => {
  const [logs, setLogs] = useState([]);
  const logContainerRef = useRef(null);

  useImperativeHandle(ref, () => ({
    addLogEntry(message, type = "info") {
      const timestamp = new Date().toLocaleTimeString();
      setLogs((prev) => [...prev, { text: `${timestamp} - ${type.toUpperCase()} - ${message}`, type }]);
    },
  }));

  const clearLog = () => setLogs([]);
  const toggleAutoScroll = () => {
    if (setAutoScroll) setAutoScroll(!autoScroll);
  };

  useEffect(() => {
    if (autoScroll && logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [logs, autoScroll]);

  return (
    <div className="log-section">
      <div className="card">
        <h3>Log Systemu</h3>
        <div className="header">
          <button onClick={clearLog}>Wyczyść</button>
          <button onClick={toggleAutoScroll}>Auto-scroll: <span>{autoScroll ? "ON" : "OFF"}</span></button>
        </div>
      </div>
      <div id="systemLog" ref={logContainerRef} className="log-box">
        {logs.length === 0 ? (<p className="empty">Brak logów...</p>) : (
          logs.map((entry, idx) => (
            <div key={idx} className={entry.type}>{entry.text}</div>
          ))
        )}
      </div>
    </div>
  );
});

export default SystemLog;
