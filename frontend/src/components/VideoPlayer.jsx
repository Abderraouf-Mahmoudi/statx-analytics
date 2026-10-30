import { useEffect, useMemo, useRef, useState } from "react";
import {
  getClipStreamUrl,
  trimMatchVideo,
  uploadMatchVideo,
} from "../services/api";


function formatTimecode(totalSeconds) {
  const safeSeconds = Math.max(0, Math.floor(Number(totalSeconds) || 0));
  const hours = Math.floor(safeSeconds / 3600);
  const minutes = Math.floor((safeSeconds % 3600) / 60);
  const seconds = safeSeconds % 60;
  return [hours, minutes, seconds].map((value) => String(value).padStart(2, "0")).join(":");
}


function formatBytes(bytes) {
  if (!bytes) return "0 MB";
  const units = ["B", "KB", "MB", "GB"];
  const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  return `${(bytes / 1024 ** index).toFixed(index > 1 ? 1 : 0)} ${units[index]}`;
}


function UploadIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-6 w-6" fill="none" stroke="currentColor" strokeWidth="1.7" aria-hidden="true">
      <path d="M12 16V4m0 0L7.5 8.5M12 4l4.5 4.5" />
      <path d="M5 14v5h14v-5" />
    </svg>
  );
}


function ScissorsIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
      <circle cx="6" cy="7" r="3" /><circle cx="6" cy="17" r="3" />
      <path d="m8.7 8.4 10.8 6.1M8.7 15.6 19.5 9.5" />
    </svg>
  );
}


export default function VideoPlayer() {
  const videoRef = useRef(null);
  const inputRef = useRef(null);
  const [sourceFile, setSourceFile] = useState(null);
  const [sourceUrl, setSourceUrl] = useState("");
  const [videoId, setVideoId] = useState("");
  const [duration, setDuration] = useState(0);
  const [currentTime, setCurrentTime] = useState(0);
  const [startTime, setStartTime] = useState(0);
  const [endTime, setEndTime] = useState(0);
  const [uploading, setUploading] = useState(false);
  const [trimming, setTrimming] = useState(false);
  const [clip, setClip] = useState(null);
  const [playbackMode, setPlaybackMode] = useState("source");
  const [error, setError] = useState("");
  const [dragActive, setDragActive] = useState(false);

  useEffect(() => () => {
    if (sourceUrl) URL.revokeObjectURL(sourceUrl);
  }, [sourceUrl]);

  const clipDuration = Math.max(0, endTime - startTime);
  const safeDuration = Math.max(duration, 1);
  const selectionStyle = useMemo(() => ({
    left: `${(startTime / safeDuration) * 100}%`,
    right: `${100 - (endTime / safeDuration) * 100}%`,
  }), [startTime, endTime, safeDuration]);
  const playbackUrl = playbackMode === "clip" && clip
    ? getClipStreamUrl(clip.clip_id)
    : sourceUrl;

  async function selectFile(file) {
    if (!file) return;
    if (file.type !== "video/mp4" && !file.name.toLowerCase().endsWith(".mp4")) {
      setError("Sélectionnez un fichier de match au format MP4.");
      return;
    }
    setError("");
    setClip(null);
    setPlaybackMode("source");
    setVideoId("");
    setDuration(0);
    setStartTime(0);
    setEndTime(0);
    setSourceFile(file);
    setSourceUrl(URL.createObjectURL(file));
    setUploading(true);
    try {
      const uploaded = await uploadMatchVideo(file);
      setVideoId(uploaded.video_id);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setUploading(false);
    }
  }

  function handleLoadedMetadata(event) {
    const videoDuration = Number.isFinite(event.currentTarget.duration)
      ? Math.floor(event.currentTarget.duration)
      : 0;
    setDuration(videoDuration);
    setEndTime(videoDuration);
  }

  function handleStartChange(value) {
    const next = Math.min(Number(value), Math.max(endTime - 1, 0));
    setStartTime(next);
    if (videoRef.current && playbackMode === "source") videoRef.current.currentTime = next;
  }

  function handleEndChange(value) {
    const next = Math.max(Number(value), Math.min(startTime + 1, safeDuration));
    setEndTime(next);
    if (videoRef.current && playbackMode === "source") videoRef.current.currentTime = next;
  }

  async function handleTrim() {
    if (!videoId || clipDuration <= 0) return;
    setError("");
    setTrimming(true);
    try {
      const result = await trimMatchVideo({
        videoId,
        startTime: formatTimecode(startTime),
        endTime: formatTimecode(endTime),
      });
      setClip(result);
      setPlaybackMode("clip");
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setTrimming(false);
    }
  }

  return (
    <section className="space-y-5">
      <div className="flex flex-col gap-3 rounded-2xl border border-slate-800 bg-card px-5 py-4 shadow-card md:flex-row md:items-center md:justify-between">
        <div>
          <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.2em] text-emerald-400">
            <span>Module 01 · Video Engine</span><span className="h-1 w-1 rounded-full bg-emerald-400" /><span>Feed local</span>
          </div>
          <h2 className="mt-1 text-xl font-black tracking-tight text-white">Video Studio · Découpage du match</h2>
          <p className="mt-1 text-sm text-slate-400">Importez le match, placez les deux repères et exportez la séquence sans ré-encodage lourd.</p>
        </div>
        <div className="flex items-center gap-2 rounded-lg border border-emerald-400/15 bg-emerald-400/5 px-3 py-2 text-[11px] font-semibold text-emerald-300">
          <span className="h-2 w-2 animate-pulse rounded-full bg-emerald-400" /> FFmpeg · Stream copy
        </div>
      </div>

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1.65fr)_360px]">
        <div className="space-y-5">
          <article className="overflow-hidden rounded-2xl border border-slate-800 bg-[#111827] shadow-card">
            <div className="flex items-center justify-between border-b border-slate-800 px-4 py-3 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
              <span>{playbackMode === "clip" ? "Aperçu du clip exporté" : sourceFile?.name || "Source vidéo"}</span>
              <span className="text-emerald-400">{sourceFile ? formatTimecode(currentTime) : "--:--:--"}</span>
            </div>
            {sourceUrl ? (
              <video
                key={playbackUrl}
                ref={videoRef}
                src={playbackUrl}
                controls
                preload="metadata"
                onLoadedMetadata={playbackMode === "source" ? handleLoadedMetadata : undefined}
                onTimeUpdate={(event) => setCurrentTime(event.currentTarget.currentTime)}
                className="aspect-video w-full bg-black object-contain"
              >
                Votre navigateur ne prend pas en charge la lecture vidéo HTML5.
              </video>
            ) : (
              <button
                type="button"
                onClick={() => inputRef.current?.click()}
                onDragOver={(event) => { event.preventDefault(); setDragActive(true); }}
                onDragLeave={() => setDragActive(false)}
                onDrop={(event) => { event.preventDefault(); setDragActive(false); selectFile(event.dataTransfer.files[0]); }}
                className={`grid aspect-video w-full place-items-center bg-[#090D15] px-6 text-center transition ${dragActive ? "bg-emerald-950/40" : "hover:bg-slate-950"}`}
              >
                <span>
                  <span className="mx-auto grid h-14 w-14 place-items-center rounded-2xl border border-emerald-400/20 bg-emerald-400/10 text-emerald-400"><UploadIcon /></span>
                  <span className="mt-4 block text-base font-bold text-white">Charger le match complet</span>
                  <span className="mt-1 block text-sm text-slate-500">Glissez un MP4 ici ou cliquez pour parcourir</span>
                </span>
              </button>
            )}
            <input ref={inputRef} type="file" accept="video/mp4,.mp4" className="hidden" onChange={(event) => selectFile(event.target.files?.[0])} />
          </article>

          <article className="rounded-2xl border border-slate-800 bg-card p-5 shadow-card">
            <div className="grid gap-3 sm:grid-cols-3">
              {[['Début', startTime], ['Lecture', currentTime], ['Fin', endTime]].map(([label, value]) => (
                <div key={label} className="rounded-xl border border-slate-800 bg-slate-950/45 px-4 py-3">
                  <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">{label}</p>
                  <p className={`mt-1 font-mono text-sm font-bold ${label === 'Lecture' ? 'text-emerald-400' : 'text-cyan-300'}`}>{formatTimecode(value)}</p>
                </div>
              ))}
            </div>

            <div className="mt-5 rounded-xl border border-slate-800 bg-[#090D15] px-4 py-5">
              <div className="mb-4 flex items-center justify-between text-[10px] uppercase tracking-wider text-slate-500"><span>Timeline du match</span><span className="font-mono text-emerald-400">Séquence · {formatTimecode(clipDuration)}</span></div>
              <div className="relative h-12">
                <div className="absolute left-0 right-0 top-5 h-2 rounded-full bg-slate-800" />
                <div className="absolute top-5 h-2 rounded-full bg-gradient-to-r from-cyan-400 to-emerald-400 shadow-glow" style={selectionStyle} />
                <input aria-label="Heure de début" type="range" min="0" max={safeDuration} step="1" value={startTime} disabled={!duration} onChange={(event) => handleStartChange(event.target.value)} className="video-range video-range-start" />
                <input aria-label="Heure de fin" type="range" min="0" max={safeDuration} step="1" value={endTime} disabled={!duration} onChange={(event) => handleEndChange(event.target.value)} className="video-range video-range-end" />
              </div>
              <div className="flex justify-between font-mono text-[10px] text-slate-600"><span>00:00:00</span><span>{formatTimecode(duration)}</span></div>
            </div>

            {error && <p className="mt-4 rounded-xl border border-red-400/20 bg-red-500/10 px-4 py-3 text-sm text-red-200">{error}</p>}
            <button type="button" onClick={handleTrim} disabled={!videoId || !duration || trimming || uploading} className="mt-5 inline-flex w-full items-center justify-center gap-2 rounded-xl bg-emerald-500 px-5 py-3 text-sm font-black text-emerald-950 shadow-glow transition hover:bg-emerald-400 disabled:cursor-not-allowed disabled:opacity-50 sm:w-auto">
              {trimming ? <span className="h-4 w-4 animate-spin rounded-full border-2 border-emerald-950/30 border-t-emerald-950" /> : <ScissorsIcon />}
              {uploading ? "Téléversement du match…" : trimming ? "Découpage FFmpeg en cours…" : "Découper & Analyser la Séquence"}
            </button>
          </article>
        </div>

        <aside className="space-y-5">
          <article className="rounded-2xl border border-slate-800 bg-card p-5 shadow-card">
            <div className="flex items-center justify-between"><h3 className="font-bold text-white">Séquence active</h3><span className="rounded-md bg-emerald-400/10 px-2 py-1 text-[10px] font-bold uppercase tracking-wider text-emerald-400">H.264 / HEVC</span></div>
            <dl className="mt-5 space-y-4 text-sm">
              <div className="border-b border-slate-800 pb-4"><dt className="text-xs text-slate-500">Fichier source</dt><dd className="mt-1 truncate font-semibold text-slate-200">{sourceFile?.name || "Aucun fichier"}</dd><dd className="mt-1 text-xs text-slate-600">{sourceFile ? formatBytes(sourceFile.size) : "—"}</dd></div>
              <div className="grid grid-cols-2 gap-3"><div><dt className="text-xs text-slate-500">Point d’entrée</dt><dd className="mt-1 font-mono font-bold text-cyan-300">{formatTimecode(startTime)}</dd></div><div><dt className="text-xs text-slate-500">Point de sortie</dt><dd className="mt-1 font-mono font-bold text-cyan-300">{formatTimecode(endTime)}</dd></div></div>
              <div><dt className="text-xs text-slate-500">Durée sélectionnée</dt><dd className="mt-1 text-2xl font-black text-white">{formatTimecode(clipDuration)}</dd></div>
            </dl>
          </article>

          <article className="rounded-2xl border border-slate-800 bg-card p-5 shadow-card">
            <h3 className="font-bold text-white">Clip exporté</h3>
            {clip ? (
              <div className="mt-4">
                <div className="rounded-xl border border-emerald-400/15 bg-emerald-400/5 p-4"><p className="text-xs font-bold uppercase tracking-wider text-emerald-400">Prêt pour l’analyse</p><p className="mt-2 font-mono text-xs text-slate-300">{clip.clip_id}</p><p className="mt-2 text-sm text-slate-400">{clip.start_time} → {clip.end_time}</p></div>
                <div className="mt-3 grid grid-cols-2 gap-2"><button type="button" onClick={() => setPlaybackMode("clip")} className="rounded-lg border border-emerald-400/20 bg-emerald-400/10 px-3 py-2 text-xs font-bold text-emerald-300 hover:bg-emerald-400/15">Lire le clip</button><button type="button" onClick={() => setPlaybackMode("source")} className="rounded-lg border border-slate-700 px-3 py-2 text-xs font-bold text-slate-300 hover:bg-slate-800">Match complet</button></div>
              </div>
            ) : (
              <p className="mt-3 text-sm leading-6 text-slate-500">Le clip apparaîtra ici dès que FFmpeg aura terminé le découpage.</p>
            )}
          </article>
        </aside>
      </div>
    </section>
  );
}

export { formatTimecode };

