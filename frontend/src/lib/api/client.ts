import type { ProblemDetails } from "./types";

export const API_ROOT = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000/api/v1";
export const apiUrl = (path: string) => `${API_ROOT}${path}`;

function cookie(name: string): string | undefined {
  const entry = document.cookie.split(";").map((value) => value.trim()).find((value) => value.startsWith(`${name}=`));
  return entry ? decodeURIComponent(entry.slice(name.length + 1)) : undefined;
}

export class ApiProblem extends Error {
  constructor(public readonly problem: ProblemDetails) {
    super(problem.detail);
  }
}

export async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const method = (options.method ?? "GET").toUpperCase();
  const headers = new Headers(options.headers);
  if (options.body && !(options.body instanceof FormData) && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  if (!["GET", "HEAD", "OPTIONS"].includes(method)) {
    const csrf = cookie("statx_csrf");
    if (csrf) headers.set("X-CSRF-Token", csrf);
  }
  const response = await fetch(apiUrl(path), { ...options, method, headers: Object.fromEntries(headers), credentials: "include" });
  if (!response.ok) {
    const problem = await response.json() as ProblemDetails;
    throw new ApiProblem(problem);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}
