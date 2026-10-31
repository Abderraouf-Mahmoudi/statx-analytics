import { useEffect, useState } from "react";

import { uploadPlayerPhoto, type PhotoView } from "./api";

export interface PhotoSelection { file: File; source: "camera" | "gallery" }

export function PlayerPhotoPicker({
  playerId,
  upload = uploadPlayerPhoto,
  onSelectionChange,
}: {
  playerId?: string;
  upload?: (playerId: string, source: "camera" | "gallery", file: File) => Promise<PhotoView>;
  onSelectionChange?: (selection: PhotoSelection | null) => void;
}) {
  const [selection, setSelection] = useState<PhotoSelection | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [status, setStatus] = useState<PhotoView | null>(null);
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);

  useEffect(() => () => { if (preview) URL.revokeObjectURL(preview); }, [preview]);

  function choose(file: File | undefined, source: "camera" | "gallery") {
    setError("");
    setStatus(null);
    if (!file) return;
    if (file.size > 10 * 1024 * 1024) { setError("La photo dépasse 10 Mo."); return; }
    if (preview) URL.revokeObjectURL(preview);
    const next = { file, source };
    setSelection(next);
    setPreview(URL.createObjectURL(file));
    onSelectionChange?.(next);
  }

  async function send() {
    if (!playerId || !selection) return;
    setPending(true); setError("");
    try { setStatus(await upload(playerId, selection.source, selection.file)); }
    catch { setError("Impossible d’envoyer le portrait."); }
    finally { setPending(false); }
  }

  return <section className="photo-picker">
    <div className="photo-picker__preview">{preview ? <img src={preview} alt="Aperçu du portrait" /> : <div className="portrait-placeholder" aria-hidden="true" />}</div>
    <div className="photo-picker__actions">
      <label className="touch-target secondary-action photo-input">Prendre une photo<input type="file" accept="image/*" capture="user" onChange={(event) => choose(event.target.files?.[0], "camera")} /></label>
      <label className="touch-target secondary-action photo-input">Choisir dans la galerie<input type="file" accept="image/jpeg,image/png,image/webp" onChange={(event) => choose(event.target.files?.[0], "gallery")} /></label>
      {playerId && selection && <button className="touch-target primary-action" type="button" disabled={pending} onClick={send}>{pending ? "Envoi…" : "Envoyer le portrait"}</button>}
    </div>
    {status && <p className="photo-status" role="status">{status.status === "ready" ? "Portrait prêt" : status.status === "failed" ? "Traitement échoué" : "Portrait en traitement"}</p>}
    {error && <p className="form-error" role="alert">{error}</p>}
  </section>;
}
