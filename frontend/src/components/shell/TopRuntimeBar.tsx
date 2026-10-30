import { LocalRuntimeStatus } from "./LocalRuntimeStatus";

export function TopRuntimeBar() {
  return (
    <header className="top-runtime-bar">
      <div><small>ESPACE DE TRAVAIL</small><strong>StatX Club · Saison active</strong></div>
      <LocalRuntimeStatus />
      <button className="touch-target language-button" type="button" aria-label="Changer de langue">FR</button>
    </header>
  );
}
