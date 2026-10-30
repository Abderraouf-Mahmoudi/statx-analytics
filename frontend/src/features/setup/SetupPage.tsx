import { useState, type FormEvent } from "react";
import type { SessionView } from "../../lib/api/types";
import { bootstrap as defaultBootstrap } from "./api";
import { setupSchema, type SetupPayload } from "./setupSchema";

export function SetupPage({ bootstrap = defaultBootstrap, onComplete }: { bootstrap?: (payload: SetupPayload) => Promise<SessionView>; onComplete: (session: SessionView) => void }) {
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError("");
    const values = Object.fromEntries(new FormData(event.currentTarget));
    const parsed = setupSchema.safeParse(values);
    if (!parsed.success) { setError(parsed.error.issues[0]?.message ?? "Formulaire invalide"); return; }
    setPending(true);
    try { onComplete(await bootstrap(parsed.data)); } catch { setError("Impossible de créer l’espace StatX"); } finally { setPending(false); }
  }
  return <main className="auth-page"><section className="auth-card"><p className="eyebrow">PREMIER DÉMARRAGE · LOCAL</p><h1>Configurer votre espace club</h1><p>Créez l’organisation et le premier administrateur. Vos données restent sur ce poste.</p><form onSubmit={submit} noValidate>
    <label>Nom du club<input className="touch-target" name="organization_name" /></label>
    <label>Nom administrateur<input className="touch-target" name="admin_display_name" /></label>
    <label>Adresse e-mail<input className="touch-target" name="email" type="email" /></label>
    <label>Mot de passe<input className="touch-target" name="password" type="password" /></label>
    <input type="hidden" name="country_code" value="TN" /><input type="hidden" name="default_locale" value="fr" /><input type="hidden" name="timezone" value="Africa/Tunis" />
    {error && <p className="form-error" role="alert">{error}</p>}<button className="touch-target primary-action" disabled={pending}>{pending ? "Création…" : "Créer l’espace StatX"}</button>
  </form><div className="unavailable-step"><strong>Activation de licence</strong><span>Disponible dans une prochaine version</span></div></section></main>;
}
