import type { Season, Team } from "./api";

export function RegistrationForm({ teams, seasons }: { teams: Team[]; seasons: Season[] }) {
  return <fieldset className="registration-fields">
    <legend>Inscription saisonnière</legend>
    <label>Équipe<select className="touch-target" name="team_id" required>{teams.map((team) => <option key={team.public_id} value={team.public_id}>{team.name}</option>)}</select></label>
    <label>Saison<select className="touch-target" name="season_id" required>{seasons.map((season) => <option key={season.public_id} value={season.public_id}>{season.name}</option>)}</select></label>
    <label>Numéro<input className="touch-target" name="shirt_number" type="number" min="0" max="99" required /></label>
  </fieldset>;
}
