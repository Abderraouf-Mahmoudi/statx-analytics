import type { FootballJobTitle } from "../../lib/api/types";

export interface SetupProfile {
  organization_name: string;
  admin_display_name: string;
  email: string;
  password: string;
  job_title: FootballJobTitle;
}

export function ProfileStep({ value, onChange, onNext, error }: {
  value: SetupProfile;
  onChange: (next: SetupProfile) => void;
  onNext: () => void;
  error?: string;
}) {
  const field = (key: keyof SetupProfile) => (event: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    onChange({ ...value, [key]: event.target.value });
  return <section className="wizard-step">
    <div className="wizard-heading"><p className="eyebrow">ÉTAPE 1 · IDENTITÉ</p><h1>Créer votre espace football</h1><p>Le premier compte reste propriétaire administrateur. Sa fonction football est enregistrée séparément.</p></div>
    <div className="form-grid setup-profile-grid">
      <label>Nom du club ou espace<input className="touch-target" value={value.organization_name} onChange={field("organization_name")} /></label>
      <label>Votre nom<input className="touch-target" value={value.admin_display_name} onChange={field("admin_display_name")} /></label>
      <label>Votre fonction<select className="touch-target" value={value.job_title} onChange={field("job_title")}><option value="director">Direction</option><option value="coach">Coach</option><option value="analyst">Analyste</option><option value="scout">Recruteur</option><option value="medical">Médical</option><option value="media">Média</option><option value="other">Autre</option></select></label>
      <label>Adresse e-mail<input className="touch-target" type="email" value={value.email} onChange={field("email")} /></label>
      <label>Mot de passe<input className="touch-target" type="password" value={value.password} onChange={field("password")} /></label>
    </div>
    {error && <p className="form-error" role="alert">{error}</p>}
    <div className="wizard-actions"><button className="touch-target primary-action" type="button" onClick={onNext}>Continuer vers le club</button></div>
  </section>;
}
