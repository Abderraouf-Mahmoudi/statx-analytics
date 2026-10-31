import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import type { Season, Team } from "../roster/api";
import { createSeason, createTeam, getClubData } from "./api";

export function ClubDashboardPage({ loadData = getClubData, addSeason = createSeason, addTeam = createTeam }: {
  loadData?: () => Promise<{ teams: Team[]; seasons: Season[] }>;
  addSeason?: (payload: { name: string }) => Promise<unknown>;
  addTeam?: (payload: { name: string; category?: string }) => Promise<unknown>;
}) {
  const client = useQueryClient();
  const query = useQuery({ queryKey: ["club-data"], queryFn: loadData });
  const [error, setError] = useState("");
  async function submitSeason(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError("");
    const form = event.currentTarget;
    const name = String(new FormData(form).get("name") ?? "").trim();
    if (!name) { setError("Le nom de la saison est obligatoire."); return; }
    try { await addSeason({ name }); form.reset(); await client.invalidateQueries({ queryKey: ["club-data"] }); }
    catch { setError("Impossible de créer la saison."); }
  }
  async function submitTeam(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError("");
    const form = event.currentTarget;
    const data = new FormData(form); const name = String(data.get("name") ?? "").trim(); const category = String(data.get("category") ?? "").trim();
    if (!name) { setError("Le nom de l’équipe est obligatoire."); return; }
    try { await addTeam({ name, ...(category ? { category } : {}) }); form.reset(); await client.invalidateQueries({ queryKey: ["club-data"] }); }
    catch { setError("Impossible de créer l’équipe."); }
  }
  return <section className="club-workspace">
    <header className="page-header"><div><p className="eyebrow">SYNTHÈSE CLUB · MODE LOCAL</p><h1>Centre opérationnel StatX</h1><p>Préparez les saisons et équipes avant de constituer l’effectif.</p></div></header>
    {query.isPending ? <p role="status">Chargement du club…</p> : query.isError ? <p role="alert">Impossible de charger le club.</p> : <div className="club-grid">
      <article className="management-card"><div><span className="metric-value">{query.data.seasons.length}</span><h2>Saisons</h2></div>{query.data.seasons.length ? <ul>{query.data.seasons.map((season) => <li key={season.public_id}>{season.name}</li>)}</ul> : <p>Aucune saison configurée</p>}<form className="inline-management-form" onSubmit={submitSeason}><label>Nom de la saison<input className="touch-target" name="name" placeholder="2026/27" /></label><button className="touch-target primary-action">Créer la saison</button></form></article>
      <article className="management-card"><div><span className="metric-value">{query.data.teams.length}</span><h2>Équipes</h2></div>{query.data.teams.length ? <ul>{query.data.teams.map((team) => <li key={team.public_id}>{team.name}</li>)}</ul> : <p>Aucune équipe configurée</p>}<form className="inline-management-form" onSubmit={submitTeam}><label>Nom de l’équipe<input className="touch-target" name="name" placeholder="U17" /></label><label>Catégorie<input className="touch-target" name="category" placeholder="academy" /></label><button className="touch-target primary-action">Créer l’équipe</button></form></article>
    </div>}
    {error && <p className="form-error" role="alert">{error}</p>}
  </section>;
}
