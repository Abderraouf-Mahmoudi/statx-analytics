import { useEffect, useMemo, useState } from "react";

import {
  getTunisianClubs,
  selectClub as defaultSelectClub,
  waitForSync as defaultWaitForSync,
  type ClubCatalog,
  type ProviderClub,
  type SyncRun,
} from "../integrations/apiFootballApi";
import { SyncProgress } from "./SyncProgress";

export function ClubSelectionPage({
  configured,
  loadClubs = getTunisianClubs,
  selectClub = defaultSelectClub,
  waitForSync = defaultWaitForSync,
  onComplete,
}: {
  configured: boolean;
  loadClubs?: () => Promise<ClubCatalog>;
  selectClub?: (club: ProviderClub) => Promise<SyncRun>;
  waitForSync?: (runId: string) => Promise<SyncRun>;
  onComplete: () => void;
}) {
  const [catalog, setCatalog] = useState<ClubCatalog | null>(null);
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<ProviderClub | null>(null);
  const [run, setRun] = useState<SyncRun | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!configured) return;
    let active = true;
    loadClubs().then((result) => active && setCatalog(result)).catch(() => active && setError("Impossible de joindre API-Football. Vous pouvez continuer manuellement."));
    return () => { active = false; };
  }, [configured, loadClubs]);

  const visible = useMemo(() => {
    const needle = query.trim().toLocaleLowerCase("fr");
    return (catalog?.clubs ?? []).filter((club) => club.name.toLocaleLowerCase("fr").includes(needle));
  }, [catalog, query]);

  async function confirm() {
    if (!selected) return;
    setError("");
    try {
      const queued = await selectClub(selected);
      setRun(queued);
      const completed = await waitForSync(queued.public_id);
      setRun(completed);
    } catch {
      setError("La synchronisation a échoué. Aucune donnée locale n’a été supprimée.");
    }
  }

  return <main className="auth-page club-onboarding"><section className="onboarding-panel">
    <header><p className="eyebrow">ESPACE CLUB · ÉTAPE 2/2</p><h1>Choisir votre club tunisien</h1><p>StatX importe l’effectif actuel, les photos d’identification, les résultats et le classement. Vous pourrez toujours corriger ou créer un joueur manuellement.</p></header>
    {!configured ? <div className="integration-unavailable"><h2>API-Football n’est pas configurée</h2><p>Le mode manuel reste entièrement disponible. La synchronisation pourra être activée plus tard.</p></div> : !catalog && !error ? <p role="status">Chargement des clubs tunisiens…</p> : <>
      {catalog?.stale && <p className="status-badge warning">Catalogue local hors ligne</p>}
      <label className="club-search">Rechercher un club<input className="touch-target" type="search" value={query} onChange={(event) => setQuery(event.target.value)} /></label>
      <div className="club-choice-grid">{visible.map((club) => <button key={club.provider_id} type="button" className={`club-choice touch-target ${selected?.provider_id === club.provider_id ? "is-selected" : ""}`} aria-label={`Choisir ${club.name}`} onClick={() => setSelected(club)}>
        {club.logo_url ? <img src={club.logo_url} alt="" /> : <span className="club-monogram">{club.name.slice(0, 2).toUpperCase()}</span>}
        <strong>{club.name}</strong><small>{club.league_name} · {club.season}</small>
      </button>)}</div>
    </>}
    {selected && !run && <div className="selection-confirm"><div><strong>{selected.name}</strong><span>{selected.league_name} · saison {selected.season}</span></div><button className="touch-target primary-action" type="button" onClick={confirm}>Confirmer et importer</button></div>}
    {run && <SyncProgress run={run} />}
    {error && <p className="form-error" role="alert">{error}</p>}
    <footer>
      {run?.status === "completed" ? <button className="touch-target primary-action" onClick={onComplete}>Ouvrir StatX</button> : <button className="touch-target secondary-action" onClick={onComplete}>Continuer sans import</button>}
    </footer>
  </section></main>;
}
