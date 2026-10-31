import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { PitchInvariant } from "../../app/i18n";
import { createPlayer, getRoster, getSeasons, getTeams, registerPlayer, type RosterEntry, type Season, type Team } from "./api";
import { PlayerForm, type CreateRosterPayload } from "./PlayerForm";
import { PlayerDetailPage } from "./PlayerDetailPage";

async function defaultLoad(): Promise<RosterEntry[]> {
  const [teams, seasons] = await Promise.all([getTeams(), getSeasons()]);
  if (!teams[0] || !seasons[0]) return [];
  return getRoster(teams[0].public_id, seasons[0].public_id);
}

async function defaultLoadContext(): Promise<{ teams: Team[]; seasons: Season[] }> {
  const [teams, seasons] = await Promise.all([getTeams(), getSeasons()]);
  return { teams, seasons };
}

async function defaultCreateRosterEntry(payload: CreateRosterPayload): Promise<void> {
  const player = await createPlayer(payload.player);
  const { team_id, ...registration } = payload.registration;
  await registerPlayer(team_id, { ...registration, player_id: player.public_id });
}

export function RosterPage({ loadRoster = defaultLoad, loadContext = defaultLoadContext, createRosterEntry = defaultCreateRosterEntry }: {
  loadRoster?: () => Promise<RosterEntry[]>;
  loadContext?: () => Promise<{ teams: Team[]; seasons: Season[] }>;
  createRosterEntry?: (payload: CreateRosterPayload) => Promise<void>;
}) {
  const queryClient = useQueryClient();
  const [editorOpen, setEditorOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [selectedPlayerId, setSelectedPlayerId] = useState<string | null>(null);
  const query = useQuery({ queryKey: ["roster"], queryFn: loadRoster });
  const context = useQuery({ queryKey: ["roster-context"], queryFn: loadContext, enabled: editorOpen });
  async function save(payload: CreateRosterPayload) {
    setSaving(true);
    try {
      await createRosterEntry(payload);
      setEditorOpen(false);
      await queryClient.invalidateQueries({ queryKey: ["roster"] });
    } finally { setSaving(false); }
  }
  const canCreate = Boolean(context.data?.teams.length && context.data.seasons.length);
  return <section className="roster-workspace">
    <header className="page-header"><div><p className="eyebrow">CLUB · EFFECTIF SAISONNIER</p><h1>Effectif</h1><p>Identités permanentes, inscriptions et état de publication.</p></div><button className="touch-target primary-action" onClick={() => setEditorOpen(true)}>Ajouter un joueur</button></header>
    {editorOpen && context.isPending && <p role="status">Chargement des équipes et saisons…</p>}
    {editorOpen && context.isError && <p role="alert">Impossible de préparer le formulaire.</p>}
    {editorOpen && context.data && !canCreate && <div className="empty-panel"><h2>Préparation du club requise</h2><p>Créez d’abord une saison et une équipe depuis l’accueil.</p><button className="touch-target secondary-action" onClick={() => setEditorOpen(false)}>Fermer</button></div>}
    {editorOpen && context.data && canCreate && <PlayerForm teams={context.data.teams} seasons={context.data.seasons} pending={saving} onCancel={() => setEditorOpen(false)} onSubmit={save} />}
    {selectedPlayerId && <PlayerDetailPage playerId={selectedPlayerId} onClose={() => setSelectedPlayerId(null)} />}
    {query.isPending ? <p role="status">Chargement de l’effectif…</p> : query.isError ? <p role="alert">Impossible de charger l’effectif</p> : !query.data.length ? <div className="empty-panel"><h2>Aucun joueur inscrit</h2><p>Créez une identité joueur puis inscrivez-la dans une équipe et une saison.</p></div> : <div className="roster-list">{query.data.map((player) => <article key={player.player_id} className="player-row"><span className="shirt-number">{player.shirt_number ?? "—"}</span><div><strong>{player.first_name} {player.last_name}</strong><small>{player.position ?? "Poste à définir"}</small></div><span className={`status-badge ${player.publishable ? "success" : "danger"}`}>{player.publishable ? "Publiable" : "Publication bloquée"}</span><button className="touch-target secondary-action" onClick={() => setSelectedPlayerId(player.player_id)}>Gérer</button></article>)}</div>}
    <PitchInvariant className="pitch-direction-marker" aria-label="Repère terrain invariant" />
  </section>;
}
