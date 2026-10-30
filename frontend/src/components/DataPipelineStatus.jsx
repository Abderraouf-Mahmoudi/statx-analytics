import { useEffect, useState } from "react";
import { getTrackingIngestionStatus } from "../services/api";


function MetricCard({ eyebrow, value, detail, accent = "emerald" }) {
  const valueColor = accent === "cyan" ? "text-cyan-300" : "text-emerald-400";
  return (
    <article className="rounded-2xl border border-slate-800 bg-card p-5 shadow-card">
      <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-slate-500">{eyebrow}</p>
      <p className={`mt-3 text-3xl font-black tracking-tight ${valueColor}`}>{value}</p>
      <p className="mt-2 text-xs leading-5 text-slate-500">{detail}</p>
    </article>
  );
}


export default function DataPipelineStatus({ matchId }) {
  const [pipeline, setPipeline] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!matchId) {
      setPipeline(null);
      setLoading(false);
      return undefined;
    }
    let active = true;
    setLoading(true);
    setError("");
    getTrackingIngestionStatus(matchId)
      .then((payload) => { if (active) setPipeline(payload); })
      .catch((requestError) => { if (active) setError(requestError.message); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [matchId]);

  const total = pipeline?.total_points || 0;
  const progress = pipeline?.progress || 0;
  const formattedTotal = new Intl.NumberFormat("fr-FR").format(total);

  return (
    <section className="space-y-5">
      <header className="flex flex-col gap-3 rounded-2xl border border-slate-800 bg-card px-5 py-4 shadow-card sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-emerald-400">Module 03 · Data Pipeline</p>
          <h2 className="mt-1 text-xl font-black text-white">SQLite Telemetry Engine</h2>
          <p className="mt-1 text-sm text-slate-400">Coordonnées métriques normalisées et synchronisées avec le match actif.</p>
        </div>
        <span className={`w-fit rounded-lg border px-3 py-2 text-xs font-black ${total ? "border-emerald-400/20 bg-emerald-400/10 text-emerald-300" : "border-amber-400/20 bg-amber-400/10 text-amber-200"}`}>
          {loading ? "Synchronisation…" : total ? `${formattedTotal} Points Ingested` : "En attente de données"}
        </span>
      </header>

      {error ? (
        <p className="rounded-xl border border-red-400/20 bg-red-500/10 px-4 py-3 text-sm text-red-200">{error}</p>
      ) : (
        <>
          <div className="grid gap-4 md:grid-cols-3">
            <MetricCard eyebrow="Coordonnées enregistrées" value={loading ? "—" : formattedTotal} detail="Points joueur stockés dans statx.db" />
            <MetricCard eyebrow="Intégrité base de données" value={`${progress}%`} detail={total ? "Transaction SQLite synchronisée" : "Aucune trajectoire ingérée"} accent="cyan" />
            <MetricCard eyebrow="État du pipeline" value={total ? "READY" : "IDLE"} detail="Upsert groupé · contraintes terrain actives" />
          </div>

          <article className="rounded-2xl border border-slate-800 bg-card p-5 shadow-card">
            <div className="flex items-center justify-between gap-4">
              <div><h3 className="font-bold text-white">Progression de l’ingestion</h3><p className="mt-1 text-xs text-slate-500">Match #{matchId}</p></div>
              <strong className="text-sm text-emerald-400">{progress}%</strong>
            </div>
            <div className="mt-4 h-2.5 overflow-hidden rounded-full bg-slate-800">
              <div className="h-full rounded-full bg-gradient-to-r from-cyan-400 to-emerald-400 transition-all duration-500" style={{ width: `${progress}%` }} />
            </div>
            <div className="mt-5 flex flex-col gap-2 rounded-xl border border-slate-800 bg-slate-950/45 px-4 py-3 text-sm sm:flex-row sm:items-center sm:justify-between">
              <span className="text-slate-400">Total des coordonnées présentes en BDD</span>
              <span className="font-mono font-black text-white">{formattedTotal}</span>
            </div>
          </article>
        </>
      )}
    </section>
  );
}
