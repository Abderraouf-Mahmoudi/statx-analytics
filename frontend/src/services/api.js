const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api"
).replace(/\/$/, "");

const API_ORIGIN = new URL(API_BASE_URL).origin;


async function request(path, options = {}) {
  const { headers, ...requestOptions } = options;
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...requestOptions,
    headers: { Accept: "application/json", ...headers },
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


export async function getTrackingIngestionStatus(matchId) {
  const response = await request(`/matches/${matchId}/tracking-status`);
  return response.json();
}


export async function ingestMatchTracking(matchId, payload) {
  const response = await request(`/matches/${matchId}/ingest-tracking`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return response.json();
}


export async function getTacticalInsights(matchId, teamId = null) {
  const query = teamId ? `?team_id=${encodeURIComponent(teamId)}` : "";
  const response = await request(`/matches/${matchId}/tactical-insights${query}`);
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


export async function uploadMatchVideo(file) {
  const formData = new FormData();
  formData.append("file", file);
  const response = await request("/video/upload", {
    method: "POST",
    body: formData,
  });
  return response.json();
}


export async function trimMatchVideo({ videoId, startTime, endTime }) {
  const response = await request("/video/trim", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      video_id: videoId,
      start_time: startTime,
      end_time: endTime,
    }),
  });
  return response.json();
}


export function getClipStreamUrl(clipId) {
  return `${API_BASE_URL}/video/stream/${clipId}`;
}

