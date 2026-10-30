import { useQuery } from "@tanstack/react-query";
import { getRoster, getSeasons, getTeams, type RosterEntry } from "./api";
import { PitchInvariant } from "../../app/i18n";

async function defaultLoad(): Promise<RosterEntry[]> {
  const [teams, seasons] = await Promise.all([getTeams(), getSeasons()]);
  if (!teams[0] || !seasons[0]) return [];
  return getRoster(teams[0].public_id, seasons[0].public_id);
}

export function RosterPage({ loadRoster = defaultLoad }: { loadRoster?: () => Promise<RosterEntry[]> }) {
  const query = useQuery({ queryKey: ["roster"], queryFn: loadRoster });
  return <section className="roster-workspace"><header className="page-header"><div><p className="eyebrow">CLUB · EFFECTIF SAISONNIER</p><h1>Effectif</h1><p>Identités permanentes, inscriptions et état de publication.</p></div><button className="touch-target primary-action">Ajouter un joueur</button></header>
    {query.isPending ? <p role="status">Chargement de l’effectif…</p> : query.isError ? <p role="alert">Impossible de charger l’effectif</p> : !query.data.length ? <div className="empty-panel"><h2>Aucun joueur inscrit</h2><p>Créez une identité joueur puis inscrivez-la dans une équipe et une saison.</p></div> : <div className="roster-list">{query.data.map((player) => <article key={player.player_id} className="player-row"><span className="shirt-number">{player.shirt_number ?? "—"}</span><div><strong>{player.first_name} {player.last_name}</strong><small>{player.position ?? "Poste à définir"}</small></div><span className={`status-badge ${player.publishable ? "success" : "danger"}`}>{player.publishable ? "Publiable" : "Publication bloquée"}</span></article>)}</div>}
    <PitchInvariant className="pitch-direction-marker" aria-label="Repère terrain invariant" />
  </section>;
}
