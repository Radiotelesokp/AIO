import { Routes, Route } from "react-router-dom";
import './App.scss';
import ControllerRadiotelescope from "./components/ControllerRadiotelescope";
import Header from "./components/Header";
import Home from "./components/Home";
import PlannerObservation from "./components/PlannerObservation";

function App() {
  return (
    <div className="App">
      <Header />
      <main>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/controller" element={<ControllerRadiotelescope />} />
          <Route path="/planner" element={<PlannerObservation />} />
        </Routes>
      </main>
    </div>
  );
}

export default App;
