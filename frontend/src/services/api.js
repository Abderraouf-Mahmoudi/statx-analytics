const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api"
).replace(/\/$/, "");

const API_ORIGIN = new URL(API_BASE_URL).origin;


async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { Accept: "application/json", ...options.headers },
    ...options,
  });

  if (!response.ok) {
    let detail = `Erreur API (${response.status})`;
    try {
      const payload = await response.json();
      detail = payload.detail || detail;
    } catch {
      // Keep the generic error when the response is not JSON.
    }
    throw new Error(detail);
  }
  return response;
}


export async function getMatchAnalytics(matchId) {
  const response = await request(`/matches/${matchId}/analytics`);
  return response.json();
}


export async function getTeams() {
  const response = await request("/teams");
  return response.json();
}


export async function getMatches() {
  const response = await request("/matches");
  return response.json();
}


export function resolveMediaUrl(path) {
  if (!path) return "";
  if (/^https?:\/\//i.test(path)) return path;
  return new URL(path, API_ORIGIN).toString();
}


export async function downloadMatchPdf(matchId) {
  const response = await request(`/matches/${matchId}/pdf`, {
    headers: { Accept: "application/pdf" },
  });
  const blob = await response.blob();
  const disposition = response.headers.get("content-disposition") || "";
  const filenameMatch = disposition.match(/filename="?([^";]+)"?/i);
  const filename = filenameMatch?.[1] || `match_${matchId}_report.pdf`;
  const objectUrl = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = objectUrl;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(objectUrl);
}

