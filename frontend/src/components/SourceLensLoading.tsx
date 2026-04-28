import { Eye } from "lucide-react";

export default function SourceLensLoading() {
  return (
    <div className="w-full max-w-6xl mx-auto mt-8 z-10 relative animate-in fade-in duration-500">
      {/* Header */}
      <div className="flex flex-col items-center justify-center text-center mb-10">
        <div className="flex items-center gap-3 mb-3">
          <Eye className="w-6 h-6 text-cyan-500 animate-pulse" />
          <h3 className="text-2xl font-bold text-white">Scanning Source Narratives</h3>
        </div>
        <p className="text-neutral-500 text-sm max-w-md animate-pulse">
          Computing vector divergence across outlets relative to the global mean...
        </p>
      </div>

      {/* Scanning progress bar */}
      <div className="max-w-sm mx-auto mb-10">
        <div className="h-px w-full bg-neutral-800 rounded-full overflow-hidden relative">
          <div className="absolute inset-0 bg-gradient-to-r from-transparent via-cyan-500 to-transparent w-1/2 animate-[shimmer_1.8s_ease-in-out_infinite]" />
        </div>
        <p className="text-[10px] font-mono text-cyan-600 text-center mt-2 uppercase tracking-widest animate-pulse">
          EMBEDDING SOURCES // COMPUTING DIVERGENCE
        </p>
      </div>

      {/* Skeleton source cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 pb-20">
        {[0.15, 0.55, 0.85].map((score, i) => (
          <div
            key={i}
            className="bg-neutral-900/50 border border-neutral-800 rounded-2xl p-6 flex flex-col gap-4"
            style={{ animationDelay: `${i * 150}ms` }}
          >
            {/* Source name + badge skeleton */}
            <div className="flex justify-between items-start">
              <div className="space-y-2">
                <div className="h-5 w-32 bg-neutral-800 rounded-md animate-pulse" />
                <div className="h-3 w-16 bg-neutral-800/60 rounded-md animate-pulse" />
              </div>
              <div className={`h-5 w-20 rounded-full animate-pulse ${
                score < 0.33 ? "bg-blue-950/60" : score < 0.66 ? "bg-indigo-950/60" : "bg-rose-950/60"
              }`} />
            </div>

            {/* Divergence bar skeleton */}
            <div>
              <div className="flex justify-between text-[10px] font-bold uppercase text-neutral-600 mb-1.5">
                <span>Central</span>
                <span>Distinctive</span>
              </div>
              <div className="h-2 w-full bg-neutral-950 rounded-full overflow-hidden relative border border-neutral-800">
                <div className="absolute inset-0 bg-gradient-to-r from-blue-500/10 via-indigo-500/10 to-rose-500/10" />
                <div
                  className="absolute top-0 left-0 h-full bg-gradient-to-r from-blue-500 via-indigo-500 to-rose-500 opacity-40 transition-all duration-1000"
                  style={{ width: `${score * 100}%` }}
                />
                <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent -translate-x-full animate-[shimmer_1.8s_ease-in-out_infinite]" />
              </div>
            </div>

            {/* Article title skeleton */}
            <div className="mt-auto pt-4 border-t border-neutral-800/60 space-y-2">
              <div className="h-3 w-24 bg-neutral-800/50 rounded animate-pulse" />
              <div className="h-4 w-full bg-neutral-800 rounded-md animate-pulse" />
              <div className="h-4 w-3/4 bg-neutral-800/60 rounded-md animate-pulse" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
