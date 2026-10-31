import { request } from "../../lib/api/client";
import { getSeasons, getTeams, type Season, type Team } from "../roster/api";

export async function getClubData(): Promise<{ teams: Team[]; seasons: Season[] }> {
  const [teams, seasons] = await Promise.all([getTeams(), getSeasons()]);
  return { teams, seasons };
}
export const createSeason = (payload: { name: string }) => request<Season>("/seasons", { method: "POST", body: JSON.stringify(payload) });
export const createTeam = (payload: { name: string; category?: string }) => request<Team>("/teams", { method: "POST", body: JSON.stringify(payload) });
