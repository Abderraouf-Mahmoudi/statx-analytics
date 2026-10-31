import { request } from "../../lib/api/client";

export interface ProviderClub {
  provider_id: string;
  name: string;
  logo_url: string | null;
  league_provider_id: string;
  league_name: string;
  season: number;
}

export interface SyncSummary {
  teams: number;
  players: number;
  fixtures: number;
  standings: number;
  absent: number;
}

export interface SyncRun {
  public_id: string;
  status: "queued" | "processing" | "completed" | "failed";
  call_count?: number;
  remaining_quota?: number | null;
  result_summary?: SyncSummary | null;
  error_summary?: string | null;
}

export interface IntegrationStatus {
  configured: boolean;
  calls_used: number;
  remaining: number;
  selected_team: { public_id: string; name: string; logo_url?: string | null } | null;
  last_run: SyncRun | null;
}

export interface ClubCatalog {
  clubs: ProviderClub[];
  stale: boolean;
  cache_age_seconds?: number | null;
}

export const getIntegrationStatus = () => request<IntegrationStatus>("/integrations/api-football/status");
export const getTunisianClubs = () => request<ClubCatalog>("/integrations/api-football/tunisia/clubs");
export const selectClub = (club: ProviderClub) => request<SyncRun>("/integrations/api-football/select-club", { method: "POST", body: JSON.stringify({
  team_provider_id: club.provider_id,
  team_name: club.name,
  logo_url: club.logo_url,
  league_provider_id: club.league_provider_id,
  league_name: club.league_name,
  season: club.season,
}) });
export const refreshClub = () => request<SyncRun>("/integrations/api-football/sync", { method: "POST" });
export const getSyncRun = (runId: string) => request<SyncRun>(`/integrations/api-football/sync-runs/${runId}`);

export async function waitForSync(runId: string, attempts = 150): Promise<SyncRun> {
  for (let attempt = 0; attempt < attempts; attempt += 1) {
    const run = await getSyncRun(runId);
    if (run.status === "completed" || run.status === "failed") return run;
    await new Promise((resolve) => window.setTimeout(resolve, 800));
  }
  throw new Error("La synchronisation prend plus de temps que prévu");
}
