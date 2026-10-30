import { useEffect, useMemo, useState } from "react";
import LoadingSpinner from "./components/LoadingSpinner";
import DataPipelineStatus from "./components/DataPipelineStatus";
import MatchDashboard from "./components/MatchDashboard";
import TopBar from "./components/TopBar";
import VideoPlayer from "./components/VideoPlayer";
import {
  downloadMatchPdf,
  getMatchAnalytics,
  getMatches,
  getTeams,
} from "./services/api";


function ErrorBanner({ message, onDismiss }) {
  return (
    <div className="mx-auto mt-5 flex max-w-[1500px] items-start justify-between gap-4 rounded-xl border border-red-400/20 bg-red-500/10 px-4 py-3 text-sm text-red-100">
      <p>{message}</p>
      <button type="button" onClick={onDismiss} className="shrink-0 text-red-200 transition hover:text-white" aria-label="Fermer l’alerte">
        ×
      </button>
    </div>
  );
}


function EmptyState() {
  return (
    <section className="mx-auto mt-20 max-w-xl rounded-2xl border border-slate-800 bg-card px-8 py-12 text-center shadow-card">
      <div className="mx-auto grid h-14 w-14 place-items-center rounded-2xl border border-emerald-400/20 bg-emerald-400/10 text-emerald-400">
        <svg viewBox="0 0 24 24" className="h-7 w-7" fill="none" stroke="currentColor" strokeWidth="1.7" aria-hidden="true">
          <path d="M4 5h16v14H4z" />
          <path d="M12 5v14M4 12h16" />
          <circle cx="12" cy="12" r="2.7" />
        </svg>
      </div>
      <h2 className="mt-5 text-xl font-bold text-white">Aucun match disponible</h2>
      <p className="mt-2 text-sm leading-6 text-slate-400">
        Ajoutez d’abord des équipes, un match et ses événements via l’API FastAPI.
        Le dashboard se synchronisera automatiquement au prochain chargement.
      </p>
    </section>
  );
}


export default function App() {
  const [activeModule, setActiveModule] = useState("analytics");
  const [teams, setTeams] = useState([]);
  const [matches, setMatches] = useState([]);
  const [activeMatchId, setActiveMatchId] = useState("");
  const [analytics, setAnalytics] = useState(null);
  const [catalogLoading, setCatalogLoading] = useState(true);
  const [analyticsLoading, setAnalyticsLoading] = useState(false);
  const [pdfLoading, setPdfLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    async function loadCatalog() {
      try {
        const [teamData, matchData] = await Promise.all([getTeams(), getMatches()]);
        if (!active) return;
        setTeams(teamData);
        setMatches(matchData);
        if (matchData.length) setActiveMatchId(String(matchData[0].id));
      } catch (requestError) {
        if (active) setError(requestError.message);
      } finally {
        if (active) setCatalogLoading(false);
      }
    }
    loadCatalog();
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!activeMatchId) {
      setAnalytics(null);
      return undefined;
    }
    let active = true;
    setAnalyticsLoading(true);
    setError("");
    getMatchAnalytics(activeMatchId)
      .then((payload) => {
        if (active) setAnalytics(payload);
      })
      .catch((requestError) => {
        if (active) setError(requestError.message);
      })
      .finally(() => {
        if (active) setAnalyticsLoading(false);
      });
    return () => {
      active = false;
    };
  }, [activeMatchId]);

  const teamsById = useMemo(
    () => Object.fromEntries(teams.map((team) => [team.id, team])),
    [teams]
  );

  async function handlePdfDownload() {
    if (!activeMatchId) return;
    setPdfLoading(true);
    setError("");
    try {
      await downloadMatchPdf(activeMatchId);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setPdfLoading(false);
    }
  }

  if (catalogLoading) {
    return (
      <div className="grid min-h-screen place-items-center bg-pitch-dark">
        <LoadingSpinner label="Connexion au moteur StatX…" size="large" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-pitch-dark text-slate-100">
      <div className="pitch-glow" aria-hidden="true" />
      <TopBar
        matches={matches}
        teamsById={teamsById}
        activeMatchId={activeMatchId}
        onMatchChange={setActiveMatchId}
        analytics={analytics}
        onDownload={handlePdfDownload}
        pdfLoading={pdfLoading}
        activeModule={activeModule}
      />
      {error && <ErrorBanner message={error} onDismiss={() => setError("")} />}
      <main className="relative mx-auto max-w-[1500px] px-4 pb-12 pt-6 sm:px-6 lg:px-8">
        <nav className="mb-6 flex w-full gap-2 overflow-x-auto rounded-xl border border-slate-800 bg-card p-1.5 sm:w-fit" aria-label="Modules StatX">
          <button type="button" onClick={() => setActiveModule("analytics")} className={`whitespace-nowrap rounded-lg px-4 py-2 text-sm font-bold transition ${activeModule === "analytics" ? "bg-emerald-500 text-emerald-950" : "text-slate-400 hover:bg-slate-800 hover:text-white"}`}>Dashboard Analytics</button>
          <button type="button" onClick={() => setActiveModule("video")} className={`whitespace-nowrap rounded-lg px-4 py-2 text-sm font-bold transition ${activeModule === "video" ? "bg-emerald-500 text-emerald-950" : "text-slate-400 hover:bg-slate-800 hover:text-white"}`}>Video Studio · Module 1</button>
          <button type="button" onClick={() => setActiveModule("pipeline")} className={`whitespace-nowrap rounded-lg px-4 py-2 text-sm font-bold transition ${activeModule === "pipeline" ? "bg-emerald-500 text-emerald-950" : "text-slate-400 hover:bg-slate-800 hover:text-white"}`}>Data Pipeline · Module 3</button>
        </nav>
        {activeModule === "pipeline" ? (
          <DataPipelineStatus matchId={activeMatchId} />
        ) : activeModule === "video" ? (
          <VideoPlayer />
        ) : !matches.length ? (
          <EmptyState />
        ) : analyticsLoading || !analytics ? (
          <div className="grid min-h-[55vh] place-items-center">
            <LoadingSpinner label="Calcul des métriques et génération des cartes…" size="large" />
          </div>
        ) : (
          <MatchDashboard analytics={analytics} onDownload={handlePdfDownload} pdfLoading={pdfLoading} />
        )}
      </main>
    </div>
  );
}

