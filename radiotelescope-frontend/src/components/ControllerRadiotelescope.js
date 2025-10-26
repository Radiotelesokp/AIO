import { useState, useRef } from "react";
import "./styles/ControllerRadiotelescope.scss"
import SystemLog from "./ControlPanel/SystemLog";
import StatusOfAntenna from "./ControlPanel/StatusOfAntenna";



export default function ControllerRadiotelescope() {
  const [autoScroll, setAutoScroll] = useState(true);
  const logRef = useRef(null);

  function log(message, type = "info") {
    if (logRef.current && logRef.current.addLogEntry) {
      logRef.current.addLogEntry(message, type);
    } else {
      console.log(`[${type}] ${message}`);
    }
  }

  function updateControlsState() {
    log("Controls updated", "info");
  }

  return (
    <div className="controller-layout">
      <StatusOfAntenna log={log} updateControlsState={updateControlsState} />
      <SystemLog ref={logRef} autoScroll={autoScroll} setAutoScroll={setAutoScroll} />
    </div>
  );
}
