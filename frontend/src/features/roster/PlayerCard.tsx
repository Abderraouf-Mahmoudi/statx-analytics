import { apiUrl } from "../../lib/api/client";
import type { RosterEntry } from "./api";

const sourceLabel: Record<string, string> = {
  api_football: "API-Football",
  club: "Club",
  manual: "Manuel",
};

const footLabel: Record<string, string> = { left: "Gauche", right: "Droit", both: "Deux pieds" };

const photoStateLabel = {
  no_photo: "Ajouter une photo",
  pending: "Portrait en attente",
  processing: "Détourage en cours",
  failed: "Réessayer le portrait",
} as const;

export function PlayerCard({ player, onManage, onPhotoAction }: { player: RosterEntry; onManage: () => void; onPhotoAction?: () => void }) {
  const name = `${player.first_name} ${player.last_name}`.trim();
  const hasPhoto = player.photo_status === "ready";
  const photoState = player.photo_status ?? "no_photo";
  const photoLabel = photoState === "ready" ? null : photoStateLabel[photoState];
  return <article className={`player-card ${player.provider_absent ? "is-stale" : ""}`}>
    <div className="player-card__frame" aria-hidden="true" />
    <div className="player-card__portrait">
      {hasPhoto ? <img src={apiUrl(`/players/${player.player_id}/photo`)} alt={`Portrait de ${name}`} /> : <div className="player-card__silhouette" role="img" aria-label={`Portrait indisponible pour ${name}`}><span /></div>}
      <span className="player-card__number">#{player.shirt_number ?? "—"}</span>
    </div>
    <div className="player-card__identity"><h2>{name}</h2><p>{player.position ?? "Poste à définir"} · {footLabel[player.preferred_foot ?? ""] ?? "Pied non renseigné"}</p></div>
    <div className="player-card__badges">
      <span className="source-badge">{sourceLabel[player.source ?? "manual"] ?? player.source}</span>
      <span className={`status-badge ${player.publishable ? "success" : "danger"}`}>{player.publishable ? "Publiable" : "Publication bloquée"}</span>
      {player.photo_rights_status === "provider_identification_only" && <span className="rights-badge">Identification uniquement</span>}
      {player.provider_absent && <span className="status-badge warning">Absent du dernier effectif API</span>}
    </div>
    {!hasPhoto && (photoState === "no_photo" || photoState === "failed")
      ? <button className="touch-target secondary-action" type="button" onClick={onPhotoAction}>{photoLabel}</button>
      : !hasPhoto && <span className="status-badge warning" role="status">{photoLabel}</span>}
    <button className="touch-target player-card__action" type="button" aria-label={`Gérer ${name}`} onClick={onManage}>Gérer le joueur</button>
  </article>;
}
