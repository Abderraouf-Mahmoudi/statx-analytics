import type { SessionView } from "../../lib/api/types";
import { bootstrap as defaultBootstrap } from "./api";
import type { SetupPayload } from "./setupSchema";
import { SetupWizard } from "./SetupWizard";

export function SetupPage({ bootstrap = defaultBootstrap, onComplete }: { bootstrap?: (payload: SetupPayload) => Promise<SessionView>; onComplete: (session: SessionView) => void }) {
  return <SetupWizard bootstrap={bootstrap} onComplete={onComplete} />;
}
