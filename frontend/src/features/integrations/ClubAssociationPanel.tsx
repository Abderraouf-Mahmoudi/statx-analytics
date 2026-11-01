import { useEffect, useState } from "react";
import { getTunisianClubs, selectClub as defaultSelectClub, type ClubCatalog, type ProviderClub, type SyncRun } from "./apiFootballApi";
import { SyncProgress } from "../onboarding/SyncProgress";

export function ClubAssociationPanel({ loadCatalog = getTunisianClubs, selectClub = defaultSelectClub }: {
  loadCatalog?: () => Promise<ClubCatalog>;
  selectClub?: (club: ProviderClub) => Promise<SyncRun>;
}) {
  const [catalog, setCatalog] = useState<ClubCatalog | null>(null);
  const [selected, setSelected] = useState<ProviderClub | null>(null);
  const [run, setRun] = useState<SyncRun | null>(null);
  const [error, setError] = useState("");
  useEffect(() => { let active = true; loadCatalog().then((value) => active && setCatalog(value)).catch(() => active && setError("Catalogue indisponible")); return () => { active = false; }; }, [loadCatalog]);
  async function associate() { if (!selected) return; setError(""); try { setRun(await selectClub(selected)); } catch { setError("Impossible d’associer ce club."); } }
  return <section className="management-card club-association"><p className="eyebrow">ADMINISTRATION · DONNÉES OFFICIELLES</p><h1>Associer le club à API-Football</h1><p>Cette action importe les données officielles sans supprimer les modifications locales du club.</p>
    {!catalog && !error && <p role="status">Chargement des clubs…</p>}<div className="club-choice-grid">{catalog?.clubs.map((club) => <button className={`club-choice touch-target ${selected?.provider_id === club.provider_id ? "is-selected" : ""}`} key={club.provider_id} aria-label={`Choisir ${club.name}`} onClick={() => setSelected(club)}><strong>{club.name}</strong><small>{club.league_name} · {club.season}</small></button>)}</div>
    {selected && <button className="touch-target primary-action" onClick={() => void associate()}>Associer et importer</button>}{run && <SyncProgress run={run} />}{error && <p className="form-error" role="alert">{error}</p>}
  </section>;
}
