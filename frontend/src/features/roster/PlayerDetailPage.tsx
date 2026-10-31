import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { getConsents, getPlayer, recordConsent, revokePlayerConsent, type ConsentView, type PlayerView } from "./api";
import { ConsentPanel } from "./ConsentPanel";

type Detail = { player: PlayerView; consents: ConsentView[] };

async function defaultLoad(playerId: string): Promise<Detail> {
  const [player, consents] = await Promise.all([getPlayer(playerId), getConsents(playerId)]);
  return { player, consents };
}

export function PlayerDetailPage({ playerId, onClose, loadDetail = defaultLoad, addConsent, revokeConsent }: {
  playerId: string;
  onClose: () => void;
  loadDetail?: (playerId: string) => Promise<Detail>;
  addConsent?: (payload: Record<string, string>) => Promise<unknown>;
  revokeConsent?: (consentId: string) => Promise<unknown>;
}) {
  const client = useQueryClient();
  const [error, setError] = useState("");
  const query = useQuery({ queryKey: ["player-detail", playerId], queryFn: () => loadDetail(playerId) });
  async function add(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError("");
    const form = event.currentTarget; const data = new FormData(form);
    const payload = { consent_type: "passport_publication", document_sha256: String(data.get("document_sha256") ?? "").trim(), guardian_name: String(data.get("guardian_name") ?? "").trim(), signed_at: new Date().toISOString() };
    if (!/^[0-9a-f]{64}$/i.test(payload.document_sha256)) { setError("L’empreinte SHA-256 doit contenir 64 caractères hexadécimaux."); return; }
    try { await (addConsent ? addConsent(payload) : recordConsent(playerId, payload)); form.reset(); await client.invalidateQueries({ queryKey: ["player-detail", playerId] }); await client.invalidateQueries({ queryKey: ["roster"] }); }
    catch { setError("Impossible d’enregistrer le consentement."); }
  }
  async function revoke(consentId: string) {
    try { await (revokeConsent ? revokeConsent(consentId) : revokePlayerConsent(playerId, consentId)); await client.invalidateQueries({ queryKey: ["player-detail", playerId] }); await client.invalidateQueries({ queryKey: ["roster"] }); }
    catch { setError("Impossible de révoquer le consentement."); }
  }
  if (query.isPending) return <section className="player-detail" role="status">Chargement du joueur…</section>;
  if (query.isError) return <section className="player-detail" role="alert">Impossible de charger le joueur.</section>;
  const { player, consents } = query.data;
  const minor = consents.some((consent) => consent.subject_is_minor) || Boolean(player.birth_date && new Date().getFullYear() - Number(player.birth_date.slice(0, 4)) < 18);
  return <section className="player-detail">
    <div className="form-heading"><div><p className="eyebrow">IDENTITÉ & CONFORMITÉ</p><h2>{player.first_name} {player.last_name}</h2></div><button className="touch-target secondary-action" onClick={onClose}>Fermer</button></div>
    <ConsentPanel isMinor={minor} consents={consents} />
    <form className="dense-form" onSubmit={add}><h3>Nouvelle preuve</h3><label>Empreinte SHA-256<input className="touch-target" name="document_sha256" maxLength={64} required /></label><label>Représentant légal<input className="touch-target" name="guardian_name" /></label>{error && <p className="form-error" role="alert">{error}</p>}<button className="touch-target primary-action">Enregistrer le consentement</button></form>
    {consents.filter((consent) => consent.status === "active").map((consent) => <button key={consent.public_id} className="touch-target danger-action" onClick={() => void revoke(consent.public_id)}>Révoquer</button>)}
  </section>;
}
