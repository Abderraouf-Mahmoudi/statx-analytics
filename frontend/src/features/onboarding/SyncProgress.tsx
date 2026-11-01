import type { SyncRun } from "../integrations/apiFootballApi";

export function SyncProgress({ run }: { run: SyncRun }) {
  const active = run.status === "queued" || run.status === "processing";
  return <section className="sync-progress" aria-live="polite">
    <div className="sync-progress__header">
      <span className={`runtime-dot ${active ? "is-pulsing" : ""}`} />
      <strong>{active ? "Synchronisation du club…" : run.status === "completed" ? "Club synchronisé" : "Synchronisation interrompue"}</strong>
    </div>
    {active && <div className="sync-progress__bar" role="progressbar" aria-label="Synchronisation en cours"><span /></div>}
    {run.stages?.length ? <div className="sync-stage-list">{run.stages.map((stage) => <span key={stage.name} className={`status-badge ${stage.status === "completed" ? "success" : stage.status === "failed" ? "danger" : "warning"}`}>{stage.name} · {stage.status}{stage.item_count ? ` (${stage.item_count})` : ""}</span>)}</div> : null}
    {run.status === "completed" && run.result_summary && <div className="sync-results">
      <strong>{run.result_summary.players} joueurs importés</strong>
      <span>{run.result_summary.fixtures} matchs · classement {run.result_summary.standings ? "disponible" : "indisponible"}</span>
    </div>}
    {run.status === "failed" && <p role="alert">{run.error_summary ?? "Le fournisseur est indisponible. Les données locales restent intactes."}</p>}
  </section>;
}
