import { Link } from "react-router-dom";
import "./styles/Header.scss";

export default function Header() {
  return (
    <header className="header">
      <div className="header-top">
        <h1>Radioteleskop</h1>
        <nav>
          <ul>
          <li><Link to="/">Strona główna</Link></li>
          <li><Link to="/controller">Sterowanie</Link></li>
          <li><Link to="/planner">Planer obserwacji</Link></li>
        </ul>
        </nav>
      </div>

      <img className="header-main" src={`${process.env.PUBLIC_URL}/SpektrumLogoBlackCanva.png`} alt="Koło Naukowe Spectrum logo"/>
    </header>
  );
}
