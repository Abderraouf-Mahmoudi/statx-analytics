function DownloadIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
      <path d="M12 3v12m0 0 4-4m-4 4-4-4" />
      <path d="M5 15v4h14v-4" />
    </svg>
  );
}


function formatMatch(match, teamsById) {
  const home = teamsById[match.home_team_id]?.name || `Équipe ${match.home_team_id}`;
  const away = teamsById[match.away_team_id]?.name || `Équipe ${match.away_team_id}`;
  const date = new Intl.DateTimeFormat("fr-FR", { day: "2-digit", month: "short", year: "numeric" }).format(new Date(match.match_date));
  return `${home} — ${away} · ${date}`;
}


export default function TopBar({ matches, teamsById, activeMatchId, onMatchChange, analytics, onDownload, pdfLoading, activeModule }) {
  return (
    <header className="relative z-10 border-b border-slate-800/80 bg-[#0B0F19]/95 backdrop-blur-xl">
      <div className="mx-auto max-w-[1500px] px-4 py-4 sm:px-6 lg:px-8">
        <div className="flex flex-col gap-5 xl:flex-row xl:items-center xl:justify-between">
          <div className="flex min-w-0 items-center gap-4">
            <div className="grid h-11 w-11 shrink-0 place-items-center rounded-xl border border-emerald-400/25 bg-emerald-400/10 font-black text-emerald-400 shadow-glow">SX</div>
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-emerald-400">Football intelligence</p>
              <h1 className="text-xl font-black tracking-tight text-white sm:text-2xl">StatX Analytics</h1>
            </div>
          </div>
          {activeModule === "video" && (
            <div className="flex items-center gap-3 rounded-xl border border-emerald-400/15 bg-emerald-400/5 px-4 py-2.5">
              <span className="h-2 w-2 animate-pulse rounded-full bg-emerald-400" />
              <div><p className="text-[10px] font-bold uppercase tracking-[0.18em] text-emerald-400">Module actif</p><p className="text-sm font-bold text-white">Video Studio · Découpage</p></div>
            </div>
          )}
          <div className={`${activeModule === "video" ? "hidden" : "flex"} flex-1 flex-col gap-3 lg:flex-row lg:items-center xl:max-w-5xl xl:justify-end`}>
            <label className="relative min-w-0 flex-1 lg:max-w-[380px]">
              <span className="sr-only">Match actif</span>
              <select value={activeMatchId} onChange={(event) => onMatchChange(event.target.value)} disabled={!matches.length} className="h-11 w-full appearance-none rounded-xl border border-slate-700 bg-card px-4 pr-10 text-sm font-medium text-slate-100 outline-none transition focus:border-emerald-400/70 focus:ring-2 focus:ring-emerald-400/10 disabled:cursor-not-allowed disabled:opacity-50">
                {!matches.length && <option>Aucun match</option>}
                {matches.map((match) => <option key={match.id} value={match.id}>{formatMatch(match, teamsById)}</option>)}
              </select>
              <svg viewBox="0 0 20 20" className="pointer-events-none absolute right-3 top-3 h-5 w-5 text-slate-500" fill="currentColor" aria-hidden="true"><path d="m5.5 7.5 4.5 4.5 4.5-4.5" /></svg>
            </label>
            {analytics && (
              <div className="flex h-11 items-center justify-center gap-4 rounded-xl border border-slate-800 bg-card px-5">
                <div className="text-right"><p className="max-w-24 truncate text-[10px] uppercase tracking-wider text-slate-500">{analytics.home.team_name}</p><p className="text-sm font-bold text-white">{analytics.home.total_xg.toFixed(2)} xG</p></div>
                <div className="rounded-lg bg-pitch-dark px-3 py-1 text-lg font-black text-emerald-400">{analytics.home.score}–{analytics.away.score}</div>
                <div><p className="max-w-24 truncate text-[10px] uppercase tracking-wider text-slate-500">{analytics.away.team_name}</p><p className="text-sm font-bold text-white">{analytics.away.total_xg.toFixed(2)} xG</p></div>
              </div>
            )}
            <button type="button" onClick={onDownload} disabled={!activeMatchId || pdfLoading} className="inline-flex h-11 items-center justify-center gap-2 rounded-xl bg-emerald-500 px-5 text-sm font-bold text-emerald-950 shadow-glow transition hover:bg-emerald-400 focus:outline-none focus:ring-2 focus:ring-emerald-300 focus:ring-offset-2 focus:ring-offset-pitch-dark disabled:cursor-not-allowed disabled:opacity-60">
              {pdfLoading ? <span className="h-4 w-4 animate-spin rounded-full border-2 border-emerald-950/30 border-t-emerald-950" aria-hidden="true" /> : <DownloadIcon />}
              {pdfLoading ? "Génération du PDF…" : "Télécharger le Rapport PDF"}
            </button>
          </div>
        </div>
      </div>
    </header>
  );
}

