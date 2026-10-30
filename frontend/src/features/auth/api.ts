import { request } from "../../lib/api/client";
import type { SessionView } from "../../lib/api/types";
export const login = (email: string, password: string) => request<SessionView>("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) });
export const getSession = () => request<SessionView>("/session");
export const logout = () => request<void>("/auth/logout", { method: "POST" });
