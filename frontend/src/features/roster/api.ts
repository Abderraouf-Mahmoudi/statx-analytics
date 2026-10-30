import { request } from "../../lib/api/client";

export interface RosterEntry { player_id: string; first_name: string; last_name: string; shirt_number: number | null; position: string | null; publishable: boolean }
export interface Team { public_id: string; name: string; category?: string | null }
export interface Season { public_id: string; name: string }
export const getTeams = () => request<Team[]>("/teams");
export const getSeasons = () => request<Season[]>("/seasons");
export const getRoster = (teamId: string, seasonId: string) => request<RosterEntry[]>(`/teams/${teamId}/roster?season_id=${seasonId}`);
export const createPlayer = (payload: unknown) => request("/players", { method: "POST", body: JSON.stringify(payload) });
export const registerPlayer = (teamId: string, payload: unknown) => request(`/teams/${teamId}/registrations`, { method: "POST", body: JSON.stringify(payload) });
export const recordConsent = (playerId: string, payload: unknown) => request(`/players/${playerId}/consents`, { method: "POST", body: JSON.stringify(payload) });
