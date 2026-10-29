import { resolveMediaUrl } from "../services/api";


function SectionHeading({ eyebrow, title, detail }) {
  return (
    <div className="mb-4 flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
      <div><p className="text-[10px] font-bold uppercase tracking-[0.22em] text-emerald-400">{eyebrow}</p><h2 className="mt-1 text-lg font-bold text-white">{title}</h2></div>
      {detail && <p className="text-xs text-slate-500">{detail}</p>}
    </div>
  );
}


function GraphCard({ title, subtitle, path, featured = false }) {
  return (
    <article className={`group overflow-hidden rounded-2xl border border-slate-800 bg-card shadow-card ${featured ? "lg:row-span-2" : ""}`}>
      <div className="flex items-center justify-between border-b border-slate-800/80 px-4 py-3"><div><h3 className="text-sm font-bold text-slate-100">{title}</h3><p className="mt-0.5 text-[11px] text-slate-500">{subtitle}</p></div><span className="h-2 w-2 rounded-full bg-emerald-400 shadow-glow" /></div>
      <div className={`overflow-hidden bg-[#0F2D1A] ${featured ? "aspect-[1.7/1]" : "aspect-[2.05/1] lg:aspect-auto lg:h-[218px]"}`}>
        <img src={resolveMediaUrl(path)} alt={title} className="h-full w-full object-cover transition duration-500 group-hover:scale-[1.015]" />
      </div>
    </article>
  );
}


function StatisticsTable({ home, away }) {
  const rows = [["Possession estimée", `${home.possession.toFixed(1)}%`, `${away.possession.toFixed(1)}%`], ["Tirs cadrés", home.shots_on_target, away.shots_on_target], ["Expected Goals", home.total_xg.toFixed(2), away.total_xg.toFixed(2)]];
  return (
    <section className="rounded-2xl border border-slate-800 bg-card p-5 shadow-card">
      <SectionHeading eyebrow="Comparatif" title="Statistiques clés" detail="Données du match" />
      <div className="overflow-hidden rounded-xl border border-slate-800">
        <table className="w-full table-fixed text-sm">
          <thead className="bg-slate-950/50 text-xs text-slate-400"><tr><th className="w-[40%] px-4 py-3 text-left font-medium">Métrique</th><th className="px-3 py-3 text-center font-semibold text-emerald-400">{home.team_name}</th><th className="px-3 py-3 text-center font-semibold text-slate-200">{away.team_name}</th></tr></thead>
          <tbody className="divide-y divide-slate-800">{rows.map(([label, homeValue, awayValue]) => <tr key={label} className="transition hover:bg-slate-800/35"><td className="px-4 py-3.5 text-slate-400">{label}</td><td className="px-3 py-3.5 text-center font-bold text-emerald-400">{homeValue}</td><td className="px-3 py-3.5 text-center font-bold text-white">{awayValue}</td></tr>)}</tbody>
        </table>
      </div>
    </section>
  );
}


function TacticalInsights({ insights, keyPlayer }) {
  return (
    <section className="rounded-2xl border border-emerald-400/15 bg-[#0D2418] p-5 shadow-card">
      <SectionHeading eyebrow="Moteur StatX" title="Avis & Alertes Tactiques StatX" detail={keyPlayer ? `Joueur clé · ${keyPlayer}` : "Synthèse automatisée"} />
      <div className="space-y-3">{insights.map((insight, index) => <div key={`${index}-${insight}`} className="flex gap-3 rounded-xl border border-emerald-400/10 bg-emerald-950/30 px-4 py-3"><span className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-emerald-400/10 text-[11px] font-black text-emerald-400">{index + 1}</span><p className="text-sm leading-6 text-emerald-50/90">{insight}</p></div>)}</div>
    </section>
  );
}


export default function MatchDashboard({ analytics }) {
  return (
    <div className="space-y-6">
      <section>
        <SectionHeading eyebrow="Match center" title="Lecture visuelle du match" detail="Cartographie StatsBomb · mise à jour à la demande" />
        <div className="grid gap-4 lg:grid-cols-[1.65fr_1fr] lg:grid-rows-2">
          <GraphCard title="Carte des tirs" subtitle="Taille proportionnelle à la valeur xG" path={analytics.graphics.shot_map} featured />
          <GraphCard title="Réseau de passes" subtitle="Directions et qualité d’exécution" path={analytics.graphics.pass_map} />
          <GraphCard title="Carte de chaleur" subtitle={analytics.key_player ? `Activité de ${analytics.key_player}` : "Zones d’activité du match"} path={analytics.graphics.heatmap} />
        </div>
      </section>
      <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
        <StatisticsTable home={analytics.home} away={analytics.away} />
        <TacticalInsights insights={analytics.tactical_insights || []} keyPlayer={analytics.key_player} />
      </div>
    </div>
  );
}

