import { useEffect, useMemo, useState } from "react";
import { getTacticalInsights } from "../services/api";


const LANES = [
  ["Flanc Gauche", "left"],
  ["Axe", "center"],
  ["Flanc Droit", "right"],
];


function LaneBar({ label, value }) {
  const critical = value > 60 && label !== "Axe";
  return (
    <div>
      <div className="mb-2 flex items-center justify-between gap-3 text-xs">
        <span className="font-semibold text-slate-300">{label}</span>
        <strong className={critical ? "text-red-400" : "text-emerald-400"}>{value.toFixed(1)}%</strong>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-slate-800">
        <div className={`h-full rounded-full transition-all duration-500 ${critical ? "bg-gradient-to-r from-orange-400 to-red-500" : "bg-gradient-to-r from-cyan-300 to-emerald-400"}`} style={{ width: `${value}%` }} />
      </div>
    </div>
  );
}


function TelemetryCard({ player }) {
  return (
    <article className="rounded-xl border border-slate-800 bg-slate-950/45 p-4">
      <div className="flex items-center justify-between gap-3">
        <div className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-cyan-400/10 text-xs font-black text-cyan-300">{player.player_name.slice(0, 2).toUpperCase()}</div>
        <span className="rounded-md bg-emerald-400/10 px-2 py-1 text-[10px] font-bold uppercase text-emerald-300">{player.samples} pts</span>
      </div>
      <h4 className="mt-3 truncate text-sm font-bold text-white">{player.player_name}</h4>
      <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
        <div><p className="text-slate-600">Distance</p><p className="mt-1 font-mono font-bold text-cyan-300">{player.distance_km.toFixed(2)} km</p></div>
        <div><p className="text-slate-600">Vitesse max</p><p className="mt-1 font-mono font-bold text-emerald-400">{player.max_speed_kmh.toFixed(1)} km/h</p></div>
      </div>
    </article>
  );
}


export default function TacticalInsights({ matchId, onDownload, pdfLoading }) {
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!matchId) return undefined;
    let active = true;
    setLoading(true);
    setError("");
    getTacticalInsights(matchId)
      .then((payload) => { if (active) setAnalysis(payload); })
      .catch((requestError) => { if (active) setError(requestError.message); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [matchId]);

  const telemetry = useMemo(
    () => (analysis?.player_telemetry || []).slice(0, 3),
    [analysis]
  );

  return (
    <section className="rounded-2xl border border-slate-800 bg-card p-5 shadow-card xl:col-span-2">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[0.22em] text-emerald-400">Module 04 · Tactical Intelligence</p>
          <h2 className="mt-1 text-lg font-black text-white">Insights tactiques automatisés</h2>
          <p className="mt-1 text-xs text-slate-500">{analysis ? `${analysis.opponent_team_name} · ${analysis.total_opponent_points} coordonnées adverses` : "Analyse des coordonnées SQLite"}</p>
        </div>
        <button type="button" onClick={onDownload} disabled={pdfLoading || !matchId} className="inline-flex items-center justify-center gap-2 rounded-xl bg-emerald-500 px-4 py-2.5 text-xs font-black text-emerald-950 transition hover:bg-emerald-400 disabled:opacity-50">
          {pdfLoading && <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-emerald-950/30 border-t-emerald-950" />}
          {pdfLoading ? "Génération…" : "Exporter le rapport PDF"}
        </button>
      </div>

      {loading ? (
        <div className="mt-6 h-40 animate-pulse rounded-xl bg-slate-800/50" />
      ) : error ? (
        <p className="mt-5 rounded-xl border border-red-400/20 bg-red-500/10 px-4 py-3 text-sm text-red-200">{error}</p>
      ) : (
        <div className="mt-6 grid gap-5 xl:grid-cols-[0.9fr_1.1fr]">
          <div className="space-y-5">
            <article className="rounded-xl border border-slate-800 bg-slate-950/35 p-4">
              <h3 className="text-sm font-bold text-white">Répartition spatiale adverse</h3>
              <div className="mt-5 space-y-5">
                {LANES.map(([label, key]) => <LaneBar key={key} label={label} value={analysis.lane_distribution[key]} />)}
              </div>
            </article>
            {analysis.alerts.length ? analysis.alerts.map((alert) => (
              <article key={alert} className="rounded-xl border border-red-400/25 bg-red-950/35 p-4 shadow-[0_0_30px_rgba(239,68,68,0.08)]">
                <p className="text-[10px] font-black uppercase tracking-[0.18em] text-red-400">Alerte critique</p>
                <p className="mt-2 text-sm font-bold leading-6 text-red-100">{alert}</p>
              </article>
            )) : (
              <article className="rounded-xl border border-emerald-400/15 bg-emerald-950/20 p-4 text-sm text-emerald-100">Aucune faiblesse latérale critique détectée.</article>
            )}
          </div>

          <div>
            <h3 className="text-sm font-bold text-white">Télémétrie joueur</h3>
            {telemetry.length ? (
              <div className="mt-4 grid gap-3 sm:grid-cols-3">{telemetry.map((player) => <TelemetryCard key={player.player_id} player={player} />)}</div>
            ) : (
              <div className="mt-4 rounded-xl border border-dashed border-slate-700 px-5 py-10 text-center text-sm text-slate-500">Ingérez les trajectoires du Module 2 pour calculer les distances et vitesses.</div>
            )}
          </div>
        </div>
      )}
    </section>
  );
}
