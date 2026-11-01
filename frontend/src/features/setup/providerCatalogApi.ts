import { request } from "../../lib/api/client";
import type { ProviderClub } from "../integrations/apiFootballApi";

export interface SetupClubCatalog {
  clubs: ProviderClub[];
  stale: boolean;
  cache_age_seconds?: number | null;
  quota?: { calls_used: number; remaining: number };
  historical_fallback: boolean;
  historical_season?: number | null;
}

export const getSetupProviderCatalog = () => request<SetupClubCatalog>("/setup/provider-catalog");
