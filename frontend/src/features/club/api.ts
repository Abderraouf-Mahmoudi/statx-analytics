import { getSeasons, getTeams } from "../roster/api";
export async function getClubSummary() { const [teams, seasons] = await Promise.all([getTeams(), getSeasons()]); return { teams: teams.length, seasons: seasons.length }; }
