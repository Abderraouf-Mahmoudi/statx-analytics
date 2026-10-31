export function LocalRuntimeStatus() {
  return (
    <div className="runtime-status" role="status" aria-label="État du poste StatX">
      <span className="runtime-dot" aria-hidden="true" />
      <span><strong>Poste local actif</strong><small>Données locales</small></span>
    </div>
  );
}
