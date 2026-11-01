import type { ProviderClub } from "../integrations/apiFootballApi";
import type { SetupClubCatalog } from "./providerCatalogApi";

export function ClubStep({ catalog, loading, error, selected, onSelect, onManual, onBack, onNext }: {
  catalog: SetupClubCatalog | null;
  loading: boolean;
  error: string;
  selected: ProviderClub | null;
  onSelect: (club: ProviderClub) => void;
  onManual: () => void;
  onBack: () => void;
  onNext: () => void;
}) {
  return <section className="wizard-step">
    <div className="wizard-heading"><p className="eyebrow">ÉTAPE 2 · CLUB</p><h1>Sélectionner votre équipe tunisienne</h1><p>L’effectif, les portraits d’identification, les matchs et le classement seront importés après la création du compte.</p></div>
    {loading && <p role="status">Chargement du catalogue tunisien…</p>}
    {catalog?.stale && <p className="status-badge warning">Catalogue local hors ligne</p>}
    {catalog?.historical_fallback && catalog.historical_season && <p className="status-badge warning" role="status">Données historiques — saison {catalog.historical_season}</p>}
    {error && <p className="form-error" role="alert">{error}</p>}
    <div className="club-choice-grid">{catalog?.clubs.map((club) => <button key={`${club.league_provider_id}:${club.provider_id}`} className={`club-choice touch-target ${selected?.provider_id === club.provider_id ? "is-selected" : ""}`} type="button" aria-label={`Choisir ${club.name}`} onClick={() => onSelect(club)}>
      {club.logo_url ? <img src={club.logo_url} alt="" /> : <span className="club-monogram">{club.name.slice(0, 2).toUpperCase()}</span>}
      <strong>{club.name}</strong><small>{club.league_name} · {club.season}</small>
    </button>)}</div>
    <div className="wizard-actions"><button className="touch-target secondary-action" type="button" onClick={onBack}>Retour</button><button className="touch-target secondary-action" type="button" onClick={onManual}>Continuer sans import</button><button className="touch-target primary-action" type="button" disabled={!selected} onClick={onNext}>Vérifier la configuration</button></div>
  </section>;
}
