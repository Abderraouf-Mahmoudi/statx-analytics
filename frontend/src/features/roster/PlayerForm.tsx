import { useState, type FormEvent } from "react";
import type { Season, Team } from "./api";
import { playerSchema, registrationSchema } from "./schemas";
import { RegistrationForm } from "./RegistrationForm";
import { PlayerPhotoPicker, type PhotoSelection } from "./PlayerPhotoPicker";

export interface CreateRosterPayload {
  player: { first_name: string; last_name: string; birth_date?: string; primary_position: string; preferred_foot?: string };
  registration: { team_id: string; season_id: string; shirt_number: number; position: string };
  photo?: PhotoSelection;
}

export function PlayerForm({ teams, seasons, pending, onCancel, onSubmit }: {
  teams: Team[]; seasons: Season[]; pending: boolean; onCancel: () => void;
  onSubmit: (payload: CreateRosterPayload) => Promise<void>;
}) {
  const [error, setError] = useState("");
  const [photo, setPhoto] = useState<PhotoSelection | null>(null);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError("");
    const values = Object.fromEntries(new FormData(event.currentTarget));
    const player = playerSchema.safeParse({
      first_name: values.first_name, last_name: values.last_name,
      birth_date: values.birth_date || undefined, primary_position: values.primary_position,
      preferred_foot: values.preferred_foot || undefined,
    });
    const registration = registrationSchema.safeParse({
      player_id: "00000000-0000-4000-8000-000000000000", season_id: values.season_id,
      shirt_number: values.shirt_number, position: values.primary_position,
    });
    if (!player.success || !registration.success) { setError("Complétez les champs obligatoires et vérifiez le numéro."); return; }
    try {
      await onSubmit({
        player: player.data,
        registration: { team_id: String(values.team_id), season_id: registration.data.season_id, shirt_number: registration.data.shirt_number, position: registration.data.position },
        photo: photo ?? undefined,
      });
    } catch { setError("Impossible de créer l’inscription. Vérifiez les doublons et réessayez."); }
  }
  return <form className="dense-form roster-editor" onSubmit={submit} noValidate>
    <div className="form-heading"><div><p className="eyebrow">NOUVELLE IDENTITÉ</p><h2>Ajouter et inscrire un joueur</h2></div><button className="touch-target secondary-action" type="button" onClick={onCancel}>Fermer</button></div>
    <div className="form-grid">
      <label>Prénom<input className="touch-target" name="first_name" autoComplete="off" required /></label>
      <label>Nom<input className="touch-target" name="last_name" autoComplete="off" required /></label>
      <label>Date de naissance<input className="touch-target" name="birth_date" type="date" /></label>
      <label>Poste principal<input className="touch-target" name="primary_position" placeholder="CM, GK, RW…" required /></label>
      <label>Pied préféré<select className="touch-target" name="preferred_foot"><option value="">Non renseigné</option><option value="right">Droit</option><option value="left">Gauche</option><option value="both">Deux pieds</option></select></label>
    </div>
    <div><p className="eyebrow">PORTRAIT JOUEUR</p><PlayerPhotoPicker onSelectionChange={setPhoto} /></div>
    <RegistrationForm teams={teams} seasons={seasons} />
    {error && <p className="form-error" role="alert">{error}</p>}
    <button className="touch-target primary-action" disabled={pending}>{pending ? "Enregistrement…" : "Créer et inscrire"}</button>
  </form>;
}
