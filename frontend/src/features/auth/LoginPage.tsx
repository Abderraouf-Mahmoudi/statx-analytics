import { useState, type FormEvent } from "react";
import type { SessionView } from "../../lib/api/types";
import { login as defaultLogin } from "./api";

export function LoginPage({ login = defaultLogin, onComplete }: { login?: (email: string, password: string) => Promise<SessionView>; onComplete: (session: SessionView) => void }) {
  const [pending, setPending] = useState(false); const [error, setError] = useState("");
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setPending(true); setError("");
    const data = new FormData(event.currentTarget);
    try { onComplete(await login(String(data.get("email")), String(data.get("password")))); }
    catch { setError("E-mail ou mot de passe incorrect"); }
    finally { setPending(false); }
  }
  return <main className="auth-page"><section className="auth-card"><p className="eyebrow">ACCÈS SÉCURISÉ · POSTE LOCAL</p><h1>Connexion StatX</h1><p>Ouvrez votre espace opérationnel club.</p><form onSubmit={submit}>
    <label>Adresse e-mail<input className="touch-target" name="email" type="email" required /></label>
    <label>Mot de passe<input className="touch-target" name="password" type="password" required /></label>
    {error && <p className="form-error" role="alert">{error}</p>}<button className="touch-target primary-action" disabled={pending}>{pending ? "Connexion…" : "Se connecter"}</button>
  </form></section></main>;
}
