interface Consent { public_id: string; status: string; document_sha256: string | null; revoked_at?: string | null }
export function ConsentPanel({ isMinor, consents }: { isMinor: boolean; consents: Consent[] }) {
  const active = consents.find((consent) => consent.status === "active");
  return <section className="consent-panel"><header><h2>Consentements & publication</h2><span className={`status-badge ${active ? "success" : "danger"}`}>{active ? "Publication autorisée" : "Publication bloquée"}</span></header>
    {isMinor && !active && <p className="consent-warning"><span aria-label="Avertissement">⚠</span> Consentement du représentant requis</p>}
    {consents.map((consent) => <article key={consent.public_id} className="consent-evidence"><span aria-hidden="true">{consent.status === "active" ? "✓" : "⊘"}</span><div><strong>{consent.status === "active" ? "Actif" : "Révoqué"}</strong><small>Preuve SHA-256 · {consent.document_sha256 ? `${consent.document_sha256.slice(0, 10)}…` : "indisponible"}</small></div></article>)}
  </section>;
}
