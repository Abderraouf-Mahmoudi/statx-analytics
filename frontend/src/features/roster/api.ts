import { request } from "../../lib/api/client";

export interface RosterEntry {
  registration_id?: string;
  player_id: string;
  first_name: string;
  last_name: string;
  shirt_number: number | null;
  position: string | null;
  publishable: boolean;
  preferred_foot?: string | null;
  source?: "manual" | "club" | "api_football";
  provider_absent?: boolean;
  photo_status?: "no_photo" | "pending" | "processing" | "ready" | "failed";
  photo_rights_status?: string | null;
  registration_status?: string;
}
export interface PhotoView { public_id: string | null; source: string | null; status: "no_photo" | "pending" | "processing" | "ready" | "failed"; rights_status?: string | null; error?: string | null }
export interface Team { public_id: string; name: string; category?: string | null }
export interface Season { public_id: string; name: string }
export interface PlayerView { public_id: string; first_name: string; last_name: string; birth_date?: string | null; display_name?: string | null; birth_place?: string | null; birth_country?: string | null; nationality?: string | null; height_cm?: number | null; weight_kg?: number | null; primary_position?: string; secondary_positions?: string[]; preferred_foot?: string | null }
export interface ConsentView { public_id: string; consent_type: string; status: string; document_sha256: string | null; subject_is_minor: boolean; guardian_name?: string | null; revoked_at?: string | null }
export const getTeams = () => request<Team[]>("/teams");
export const getSeasons = () => request<Season[]>("/seasons");
export const getRoster = (teamId: string, seasonId: string) => request<RosterEntry[]>(`/teams/${teamId}/roster?season_id=${seasonId}`);
export const createPlayer = (payload: unknown) => request<PlayerView>("/players", { method: "POST", body: JSON.stringify(payload) });
export const registerPlayer = (teamId: string, payload: unknown) => request(`/teams/${teamId}/registrations`, { method: "POST", body: JSON.stringify(payload) });
export const recordConsent = (playerId: string, payload: unknown) => request(`/players/${playerId}/consents`, { method: "POST", body: JSON.stringify(payload) });
export const getPlayer = (playerId: string) => request<PlayerView>(`/players/${playerId}`);
export const updatePlayer = (playerId: string, payload: unknown) => request<PlayerView>(`/players/${playerId}`, { method: "PATCH", body: JSON.stringify(payload) });
export const deletePlayer = (playerId: string) => request<void>(`/players/${playerId}`, { method: "DELETE" });
export const deactivateRegistration = (registrationId: string, endDate: string) => request(`/registrations/${registrationId}/deactivate`, { method: "POST", body: JSON.stringify({ end_date: endDate }) });
export const getConsents = (playerId: string) => request<ConsentView[]>(`/players/${playerId}/consents`);
export const revokePlayerConsent = (playerId: string, consentId: string) => request<ConsentView>(`/players/${playerId}/consents/${consentId}`, { method: "DELETE" });
export const uploadPlayerPhoto = (playerId: string, source: "camera" | "gallery", file: File) => {
  const body = new FormData();
  body.append("source", source);
  body.append("photo", file);
  return request<PhotoView>(`/players/${playerId}/photo`, { method: "POST", body });
};
export const getPlayerPhotoStatus = (playerId: string) => request<PhotoView>(`/players/${playerId}/photo/status`);
export const retryPlayerPhoto = (playerId: string) => request<PhotoView>(`/players/${playerId}/photo/retry`, { method: "POST" });
