import { useEffect, useState } from "react";
import type { SessionView } from "../../lib/api/types";
import { App } from "../../app/App";
import { getSetupStatus } from "../setup/api";
import { SetupPage } from "../setup/SetupPage";
import { getSession } from "./api";
import { LoginPage } from "./LoginPage";
import { getIntegrationStatus } from "../integrations/apiFootballApi";
import { ClubSelectionPage } from "../onboarding/ClubSelectionPage";

type GateState = { phase: "loading" | "setup" | "login" | "onboarding" | "app"; session?: SessionView; integrationConfigured?: boolean };

export function SessionGate() {
  const [state, setState] = useState<GateState>({ phase: "loading" });
  async function enterAuthenticated(session: SessionView) {
    try {
      const status = await getIntegrationStatus();
      const skipped = window.localStorage.getItem(`statx:onboarding-skipped:${session.organization_id}`) === "true";
      setState(status.selected_team || skipped ? { phase: "app", session } : { phase: "onboarding", session, integrationConfigured: status.configured });
    } catch { setState({ phase: "app", session }); }
  }
  useEffect(() => { let active = true; getSetupStatus().then(async ({ required }) => {
    if (!active) return; if (required) { setState({ phase: "setup" }); return; }
    try { const session = await getSession(); if (active) await enterAuthenticated(session); }
    catch { if (active) setState({ phase: "login" }); }
  }).catch(() => active && setState({ phase: "login" })); return () => { active = false; }; }, []);
  if (state.phase === "loading") return <main className="auth-page"><p role="status">Initialisation du poste local…</p></main>;
  if (state.phase === "setup") return <SetupPage onComplete={enterAuthenticated} />;
  if (state.phase === "login") return <LoginPage onComplete={enterAuthenticated} />;
  if (state.phase === "onboarding" && state.session) return <ClubSelectionPage configured={Boolean(state.integrationConfigured)} onComplete={() => {
    window.localStorage.setItem(`statx:onboarding-skipped:${state.session!.organization_id}`, "true");
    setState({ phase: "app", session: state.session });
  }} />;
  return <App />;
}
