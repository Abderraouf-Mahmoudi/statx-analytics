import type { ProviderClub } from "../integrations/apiFootballApi";
import type { SetupProfile } from "./ProfileStep";

const functions = { director: "Direction", coach: "Coach", analyst: "Analyste", scout: "Recruteur", medical: "Médical", media: "Média", other: "Autre" };

export function ConfirmationStep({ profile, club, pending, error, onBack, onSubmit }: {
  profile: SetupProfile;
  club: ProviderClub | null;
  pending: boolean;
  error: string;
  onBack: () => void;
  onSubmit: () => void;
}) {
  return <section className="wizard-step">
    <div className="wizard-heading"><p className="eyebrow">ÉTAPE 3 · CONFIRMATION</p><h1>Prêt à ouvrir StatX</h1></div>
    <div className="confirmation-grid"><article><small>Propriétaire</small><strong>{profile.admin_display_name}</strong><span>{functions[profile.job_title]} · rôle admin</span></article><article><small>Espace</small><strong>{profile.organization_name}</strong><span>{profile.email}</span></article><article><small>Club associé</small><strong>{club?.name ?? "Configuration manuelle"}</strong><span>{club ? `${club.league_name} · ${club.season}` : "Import disponible plus tard"}</span></article></div>
    {error && <p className="form-error" role="alert">{error}</p>}
    <div className="wizard-actions"><button className="touch-target secondary-action" type="button" onClick={onBack}>Retour</button><button className="touch-target primary-action" type="button" disabled={pending} onClick={onSubmit}>{pending ? "Création…" : club ? "Créer l’espace et importer" : "Créer l’espace local"}</button></div>
  </section>;
}
