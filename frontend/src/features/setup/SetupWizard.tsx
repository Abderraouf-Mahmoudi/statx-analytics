import { useEffect, useState } from "react";
import type { SessionView } from "../../lib/api/types";
import type { ProviderClub } from "../integrations/apiFootballApi";
import { bootstrap as defaultBootstrap } from "./api";
import { ClubStep } from "./ClubStep";
import { ConfirmationStep } from "./ConfirmationStep";
import { ProfileStep, type SetupProfile } from "./ProfileStep";
import { getSetupProviderCatalog, type SetupClubCatalog } from "./providerCatalogApi";
import { setupSchema, type SetupPayload } from "./setupSchema";

const initialProfile: SetupProfile = { organization_name: "", admin_display_name: "", email: "", password: "", job_title: "coach" };

export function SetupWizard({ loadCatalog = getSetupProviderCatalog, bootstrap = defaultBootstrap, onComplete }: {
  loadCatalog?: () => Promise<SetupClubCatalog>;
  bootstrap?: (payload: SetupPayload) => Promise<SessionView>;
  onComplete: (session: SessionView) => void;
}) {
  const [step, setStep] = useState(1);
  const [profile, setProfile] = useState(initialProfile);
  const [catalog, setCatalog] = useState<SetupClubCatalog | null>(null);
  const [catalogError, setCatalogError] = useState("");
  const [selected, setSelected] = useState<ProviderClub | null>(null);
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);

  useEffect(() => { let active = true; loadCatalog().then((value) => active && setCatalog(value)).catch(() => active && setCatalogError("API-Football indisponible. Le mode manuel reste disponible.")); return () => { active = false; }; }, [loadCatalog]);

  function validateProfile() {
    const result = setupSchema.omit({ selected_club: true }).safeParse({ ...profile, country_code: "TN", default_locale: "fr", timezone: "Africa/Tunis" });
    if (!result.success) { setError(result.error.issues[0]?.message ?? "Vérifiez les informations"); return; }
    setError(""); setStep(2);
  }
  async function submit() {
    const selected_club = selected ? { team_provider_id: selected.provider_id, team_name: selected.name, logo_url: selected.logo_url, league_provider_id: selected.league_provider_id, league_name: selected.league_name, season: selected.season } : undefined;
    const parsed = setupSchema.safeParse({ ...profile, country_code: "TN", default_locale: "fr", timezone: "Africa/Tunis", selected_club });
    if (!parsed.success) { setError(parsed.error.issues[0]?.message ?? "Configuration invalide"); return; }
    setPending(true); setError("");
    try {
      const session = await bootstrap(parsed.data);
      if (selected) window.localStorage.setItem(`statx:onboarding-skipped:${session.organization_id}`, "true");
      onComplete(session);
    } catch { setError("Impossible de créer l’espace StatX."); }
    finally { setPending(false); }
  }
  return <main className="auth-page setup-wizard-page"><section className="setup-wizard"><nav className="wizard-steps" aria-label="Progression de configuration"><span className={step >= 1 ? "is-active" : ""}>1 Profil</span><span className={step >= 2 ? "is-active" : ""}>2 Club</span><span className={step >= 3 ? "is-active" : ""}>3 Confirmation</span></nav>
    {step === 1 && <ProfileStep value={profile} onChange={setProfile} onNext={validateProfile} error={error} />}
    {step === 2 && <ClubStep catalog={catalog} loading={!catalog && !catalogError} error={catalogError} selected={selected} onSelect={setSelected} onBack={() => setStep(1)} onManual={() => { setSelected(null); setStep(3); }} onNext={() => setStep(3)} />}
    {step === 3 && <ConfirmationStep profile={profile} club={selected} pending={pending} error={error} onBack={() => setStep(2)} onSubmit={() => void submit()} />}
  </section></main>;
}
