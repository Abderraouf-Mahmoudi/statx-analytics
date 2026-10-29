export default function LoadingSpinner({ label = "Chargement…", size = "normal" }) {
  const sizeClass = size === "large" ? "h-9 w-9" : "h-4 w-4";
  return (
    <div className="flex flex-col items-center justify-center gap-3 text-sm text-slate-400" role="status">
      <span className={`${sizeClass} relative block`} aria-hidden="true">
        <span className="absolute inset-0 rounded-full border-2 border-emerald-400/15" />
        <span className="absolute inset-0 animate-spin rounded-full border-2 border-transparent border-t-emerald-400" />
      </span>
      <span>{label}</span>
    </div>
  );
}

