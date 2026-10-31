import { AppShell } from "../components/shell/AppShell";
import { useLocation } from "react-router-dom";
import { RosterPage } from "../features/roster/RosterPage";
import { ClubDashboardPage } from "../features/club/ClubDashboardPage";

export function App() {
  const location = useLocation();
  return (
    <AppShell>
      {location.pathname === "/roster" ? <RosterPage /> : location.pathname === "/" ? <ClubDashboardPage /> :
      <section className="shell-placeholder">
        <small>FONDATION PRODUIT · MODE LOCAL</small>
        <h1>Centre opérationnel StatX</h1>
        <p>Le socle club, les saisons et l’effectif sont prêts. Les espaces métier seront activés progressivement sans remettre le tracking expérimental au centre du parcours.</p>
      </section>}
    </AppShell>
  );
}
