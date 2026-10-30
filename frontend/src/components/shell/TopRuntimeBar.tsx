import { LocalRuntimeStatus } from "./LocalRuntimeStatus";
import { logout } from "../../features/auth/api";

export function TopRuntimeBar() {
  return (
    <header className="top-runtime-bar">
      <div><small>ESPACE DE TRAVAIL</small><strong>StatX Club · Saison active</strong></div>
      <LocalRuntimeStatus />
      <button className="touch-target language-button" type="button" aria-label="Changer de langue">FR</button>
      <button className="touch-target language-button" type="button" onClick={() => void logout().finally(() => window.location.reload())}>Déconnexion</button>
    </header>
  );
}
