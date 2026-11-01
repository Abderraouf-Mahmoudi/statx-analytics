import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { PitchInvariant } from "../../app/i18n";
import { getRoster, getSeasons, getTeams, type RosterEntry, type Season, type Team } from "./api";
import { PlayerForm, type CreateRosterPayload } from "./PlayerForm";
import { PlayerDetailPage } from "./PlayerDetailPage";
import { PlayerCard } from "./PlayerCard";
import { createRosterEntry as defaultCreateRosterEntry } from "./rosterWorkflow";

async function defaultLoad(): Promise<RosterEntry[]> {
  const [teams, seasons] = await Promise.all([getTeams(), getSeasons()]);
  if (!teams[0] || !seasons[0]) return [];
  return getRoster(teams[0].public_id, seasons[0].public_id);
}

async function defaultLoadContext(): Promise<{ teams: Team[]; seasons: Season[] }> {
  const [teams, seasons] = await Promise.all([getTeams(), getSeasons()]);
  return { teams, seasons };
}

export function RosterPage({ loadRoster = defaultLoad, loadContext = defaultLoadContext, createRosterEntry = defaultCreateRosterEntry }: {
  loadRoster?: () => Promise<RosterEntry[]>;
  loadContext?: () => Promise<{ teams: Team[]; seasons: Season[] }>;
  createRosterEntry?: (payload: CreateRosterPayload) => Promise<unknown>;
}) {
  const queryClient = useQueryClient();
  const [editorOpen, setEditorOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [selectedPlayerId, setSelectedPlayerId] = useState<string | null>(null);
  const [selectedRegistrationId, setSelectedRegistrationId] = useState<string | null>(null);
  const [positionFilter, setPositionFilter] = useState("all");
  const [sourceFilter, setSourceFilter] = useState("all");
  const [photoFilter, setPhotoFilter] = useState("all");
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
  const visibleRoster = (query.data ?? []).filter((player) =>
    (positionFilter === "all" || player.position === positionFilter)
    && (sourceFilter === "all" || (player.source ?? "manual") === sourceFilter)
    && (photoFilter === "all" || (player.photo_status ?? "no_photo") === photoFilter)
  );
  return <section className="roster-workspace">
    <header className="page-header"><div><p className="eyebrow">CLUB · EFFECTIF SAISONNIER</p><h1>Effectif</h1><p>Identités permanentes, inscriptions et état de publication.</p></div><button className="touch-target primary-action" onClick={() => setEditorOpen(true)}>Ajouter un joueur</button></header>
    {editorOpen && context.isPending && <p role="status">Chargement des équipes et saisons…</p>}
    {editorOpen && context.isError && <p role="alert">Impossible de préparer le formulaire.</p>}
    {editorOpen && context.data && !canCreate && <div className="empty-panel"><h2>Préparation du club requise</h2><p>Créez d’abord une saison et une équipe depuis l’accueil.</p><button className="touch-target secondary-action" onClick={() => setEditorOpen(false)}>Fermer</button></div>}
    {editorOpen && context.data && canCreate && <PlayerForm teams={context.data.teams} seasons={context.data.seasons} pending={saving} onCancel={() => setEditorOpen(false)} onSubmit={save} />}
    {selectedPlayerId && <PlayerDetailPage playerId={selectedPlayerId} registrationId={selectedRegistrationId ?? undefined} onClose={() => { setSelectedPlayerId(null); setSelectedRegistrationId(null); }} />}
    {!query.isPending && !query.isError && Boolean(query.data?.length) && <div className="roster-filters" aria-label="Filtres de l’effectif"><label>Poste<select className="touch-target" value={positionFilter} onChange={(event) => setPositionFilter(event.target.value)}><option value="all">Tous</option>{["GK", "RB", "CB", "LB", "DM", "CM", "AM", "RW", "LW", "ST", "OTHER"].map((code) => <option key={code}>{code}</option>)}</select></label><label>Provenance<select className="touch-target" value={sourceFilter} onChange={(event) => setSourceFilter(event.target.value)}><option value="all">Toutes</option><option value="api_football">API-Football</option><option value="manual">Manuel</option><option value="club">Club</option></select></label><label>Portrait<select className="touch-target" value={photoFilter} onChange={(event) => setPhotoFilter(event.target.value)}><option value="all">Tous</option><option value="ready">Prêt</option><option value="no_photo">Sans photo</option><option value="pending">En attente</option><option value="failed">Échec</option></select></label></div>}
    {query.isPending ? <p role="status">Chargement de l’effectif…</p> : query.isError ? <p role="alert">Impossible de charger l’effectif</p> : !query.data.length ? <div className="empty-panel"><h2>Aucun joueur inscrit</h2><p>Créez une identité joueur puis inscrivez-la dans une équipe et une saison.</p></div> : !visibleRoster.length ? <div className="empty-panel"><h2>Aucun joueur ne correspond aux filtres</h2></div> : <div className="roster-card-grid">{visibleRoster.map((player) => <PlayerCard key={player.player_id} player={player} onManage={() => { setSelectedPlayerId(player.player_id); setSelectedRegistrationId(player.registration_id ?? null); }} onPhotoAction={() => { setSelectedPlayerId(player.player_id); setSelectedRegistrationId(player.registration_id ?? null); }} />)}</div>}
    <PitchInvariant className="pitch-direction-marker" aria-label="Repère terrain invariant" />
  </section>;
}
