import { useState, type FormEvent } from "react";
import type { PlayerView } from "./api";
import { PositionSelect } from "./PositionSelect";

export function PlayerEditForm({ player, onSubmit, onCancel }: {
  player: PlayerView;
  onSubmit: (payload: Record<string, unknown>) => Promise<void>;
  onCancel: () => void;
}) {
  const [position, setPosition] = useState(player.primary_position ?? "OTHER");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setPending(true); setError("");
    const values = Object.fromEntries(new FormData(event.currentTarget));
    try {
      await onSubmit({
        first_name: String(values.first_name), last_name: String(values.last_name),
        display_name: String(values.display_name).trim() || null,
        primary_position: position,
        preferred_foot: String(values.preferred_foot).trim() || null,
      });
    } catch { setError("Impossible d’enregistrer les modifications."); }
    finally { setPending(false); }
  }
  return <form className="dense-form player-edit-form" onSubmit={submit}>
    <div className="form-grid"><label>Prénom<input className="touch-target" name="first_name" defaultValue={player.first_name} required /></label><label>Nom<input className="touch-target" name="last_name" defaultValue={player.last_name} required /></label><label>Nom d’affichage<input className="touch-target" name="display_name" defaultValue={player.display_name ?? ""} /></label><label>Poste principal<PositionSelect value={position} onChange={setPosition} required /></label><label>Pied préféré<select className="touch-target" name="preferred_foot" defaultValue={player.preferred_foot ?? ""}><option value="">Non renseigné</option><option value="right">Droit</option><option value="left">Gauche</option><option value="both">Deux pieds</option></select></label></div>
    {error && <p className="form-error" role="alert">{error}</p>}
    <div className="wizard-actions"><button className="touch-target secondary-action" type="button" onClick={onCancel}>Annuler</button><button className="touch-target primary-action" disabled={pending}>{pending ? "Enregistrement…" : "Enregistrer les modifications"}</button></div>
  </form>;
}
