import { request } from "../../lib/api/client";
import type { SessionView } from "../../lib/api/types";
import type { SetupPayload } from "./setupSchema";

export const getSetupStatus = () => request<{ required: boolean }>("/setup/status");
export const bootstrap = (payload: SetupPayload) => request<SessionView>("/setup", { method: "POST", body: JSON.stringify(payload) });
