import { request } from "../../lib/api/client";

export interface RosterEntry {
  player_id: string;
  first_name: string;
  last_name: string;
  shirt_number: number | null;
  position: string | null;
  publishable: boolean;
  preferred_foot?: string | null;
  source?: "manual" | "club" | "api_football";
  provider_absent?: boolean;
  photo_status?: "pending" | "processing" | "ready" | "failed" | null;
  photo_rights_status?: string | null;
}
export interface PhotoView { public_id: string; source: string; status: "pending" | "processing" | "ready" | "failed"; rights_status?: string; error?: string | null }
export interface Team { public_id: string; name: string; category?: string | null }
export interface Season { public_id: string; name: string }
export interface PlayerView { public_id: string; first_name: string; last_name: string; birth_date?: string | null; preferred_foot?: string | null }
export interface ConsentView { public_id: string; consent_type: string; status: string; document_sha256: string | null; subject_is_minor: boolean; guardian_name?: string | null; revoked_at?: string | null }
export const getTeams = () => request<Team[]>("/teams");
export const getSeasons = () => request<Season[]>("/seasons");
export const getRoster = (teamId: string, seasonId: string) => request<RosterEntry[]>(`/teams/${teamId}/roster?season_id=${seasonId}`);
export const createPlayer = (payload: unknown) => request<PlayerView>("/players", { method: "POST", body: JSON.stringify(payload) });
export const registerPlayer = (teamId: string, payload: unknown) => request(`/teams/${teamId}/registrations`, { method: "POST", body: JSON.stringify(payload) });
export const recordConsent = (playerId: string, payload: unknown) => request(`/players/${playerId}/consents`, { method: "POST", body: JSON.stringify(payload) });
export const getPlayer = (playerId: string) => request<PlayerView>(`/players/${playerId}`);
export const getConsents = (playerId: string) => request<ConsentView[]>(`/players/${playerId}/consents`);
export const revokePlayerConsent = (playerId: string, consentId: string) => request<ConsentView>(`/players/${playerId}/consents/${consentId}`, { method: "DELETE" });
export const uploadPlayerPhoto = (playerId: string, source: "camera" | "gallery", file: File) => {
  const body = new FormData();
  body.append("source", source);
  body.append("photo", file);
  return request<PhotoView>(`/players/${playerId}/photo`, { method: "POST", body });
};
