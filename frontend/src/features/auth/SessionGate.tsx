import { useEffect, useState } from "react";
import type { SessionView } from "../../lib/api/types";
import { App } from "../../app/App";
import { getSetupStatus } from "../setup/api";
import { SetupPage } from "../setup/SetupPage";
import { getSession } from "./api";
import { LoginPage } from "./LoginPage";

type GateState = { phase: "loading" | "setup" | "login" | "app"; session?: SessionView };

export function SessionGate() {
  const [state, setState] = useState<GateState>({ phase: "loading" });
  useEffect(() => { let active = true; getSetupStatus().then(async ({ required }) => {
    if (!active) return; if (required) { setState({ phase: "setup" }); return; }
    try { const session = await getSession(); if (active) setState({ phase: "app", session }); }
    catch { if (active) setState({ phase: "login" }); }
  }).catch(() => active && setState({ phase: "login" })); return () => { active = false; }; }, []);
  if (state.phase === "loading") return <main className="auth-page"><p role="status">Initialisation du poste local…</p></main>;
  if (state.phase === "setup") return <SetupPage onComplete={(session) => setState({ phase: "app", session })} />;
  if (state.phase === "login") return <LoginPage onComplete={(session) => setState({ phase: "app", session })} />;
  return <App />;
}
