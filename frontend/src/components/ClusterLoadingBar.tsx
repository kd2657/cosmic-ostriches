"use client";

import { useState, useEffect, useRef } from "react";

const STAGES = [
  { label: "Ingesting live news feeds", icon: "📡", duration: 2200 },
  { label: "Embedding vectors", icon: "🧮", duration: 2000 },
  { label: "Computing clusters", icon: "🧩", duration: 1800 },
  { label: "Generating narratives", icon: "✨", duration: 3000 },
];

export default function ClusterLoadingBar({ 
  currentStage, 
  progress, 
  isStreaming = false 
}: { 
  currentStage?: string, 
  progress?: number, 
  isStreaming?: boolean 
}) {
  const [simStage, setSimStage] = useState(0);
  const [simPct, setSimPct] = useState(0);
  const [simGlobalPct, setSimGlobalPct] = useState(0);
  const stageStartRef = useRef(Date.now());

  // Simulation logic for fallback
  useEffect(() => {
    if (isStreaming) return;

    const interval = setInterval(() => {
      const stage = STAGES[simStage];
      if (!stage) return;

      const elapsed = Date.now() - stageStartRef.current;
      const pct = Math.min(100, (elapsed / stage.duration) * 100);
      setSimPct(pct);

      const stageWeight = 100 / STAGES.length;
      setSimGlobalPct(Math.min(95, (simStage * stageWeight) + (pct / 100 * stageWeight)));

      if (pct >= 100 && simStage < STAGES.length - 1) {
        setSimStage(prev => prev + 1);
        stageStartRef.current = Date.now();
        setSimPct(0);
      }
    }, 50);

    return () => clearInterval(interval);
  }, [simStage, isStreaming]);

  // Determine active display values based on mode
  const activeLabel = isStreaming ? (currentStage || "Synthesizing...") : STAGES[simStage].label;
  const displayPct = isStreaming ? (progress || 0) : Math.round(simGlobalPct);
  
  // Find which stage is currently "active" in the list for UI highlighting
  let highlightIdx = -1;
  if (isStreaming && currentStage) {
    highlightIdx = STAGES.findIndex(s => currentStage.toLowerCase().includes(s.label.split(" ")[0].toLowerCase()));
    if (highlightIdx === -1) {
        // Fallback matching logic for semantic labels
        if (currentStage.toLowerCase().includes("fetch")) highlightIdx = 0;
        if (currentStage.toLowerCase().includes("embed")) highlightIdx = 1;
        if (currentStage.toLowerCase().includes("cluster")) highlightIdx = 2;
        if (currentStage.toLowerCase().includes("summary") || currentStage.toLowerCase().includes("synthes")) highlightIdx = 3;
    }
  } else {
    highlightIdx = simStage;
  }

  return (
    <div className="flex flex-col items-center justify-center gap-6 px-6 py-10 max-w-lg mx-auto">
      {/* Pulsing title */}
      <div className="text-center space-y-2">
        <h2 className="text-xl font-bold text-white font-mono tracking-tight animate-pulse">
            {isStreaming ? "Clustering" : "Clustering"}
        </h2>
        <p className="text-xs text-neutral-600 font-mono tracking-widest uppercase truncate max-w-[300px]">
          {activeLabel}
        </p>
      </div>

      {/* Main progress bar */}
      <div className="w-full space-y-2">
        <div className="relative w-full h-2 bg-neutral-900 rounded-full overflow-hidden border border-neutral-800/60 shadow-[inset_0_1px_2px_rgba(0,0,0,0.5)]">
          <div
            className="absolute inset-y-0 left-0 rounded-full transition-all duration-500 ease-out"
            style={{
              width: `${displayPct}%`,
              background: "linear-gradient(90deg, #6366f1, #8b5cf6, #a78bfa)",
              boxShadow: "0 0 15px rgba(139, 92, 246, 0.4), 0 0 40px rgba(139, 92, 246, 0.15)",
            }}
          />
        </div>
        <div className="flex justify-between items-center text-[10px] font-mono">
          <span className="text-neutral-600 uppercase tracking-tighter">
            {isStreaming ? "Clustering Progress" : `Stage ${simStage + 1}/${STAGES.length}`}
          </span>
          <span className="text-indigo-400 font-bold tabular-nums">{displayPct}%</span>
        </div>
      </div>

      {/* Stage list */}
      <div className="w-full space-y-2">
        {STAGES.map((stage, i) => {
          const isActive = i === highlightIdx;
          const isComplete = i < highlightIdx;

          return (
            <div
              key={i}
              className={`flex items-center gap-3 px-4 py-2 rounded-lg border transition-all duration-500 font-mono text-xs ${
                isActive
                  ? "bg-indigo-950/20 border-indigo-500/50 text-indigo-200 shadow-[0_0_20px_rgba(99,102,241,0.1)]"
                  : isComplete
                    ? "bg-neutral-900/40 border-neutral-800/40 text-neutral-500"
                    : "bg-transparent border-neutral-900/30 text-neutral-800"
              }`}
            >
              <div className="w-5 h-5 flex items-center justify-center shrink-0">
                {isComplete ? (
                    <span className="text-indigo-500">✓</span>
                ) : isActive ? (
                    <div className="w-2 h-2 bg-indigo-500 rounded-full animate-ping" />
                ) : (
                    <div className="w-1.5 h-1.5 bg-neutral-800 rounded-full" />
                )}
              </div>
              <span className={`flex-grow truncate ${isActive ? "font-medium" : ""}`}>
                {stage.label}
              </span>
              {isActive && isStreaming && (
                <div className="flex space-x-0.5">
                    {[1, 2, 3].map(d => <div key={d} className="w-0.5 h-1.5 bg-indigo-500 animate-pulse" style={{animationDelay: `${d*200}ms`}} />)}
                </div>
              )}
            </div>
          );
        })}
      </div>

      <p className="text-[9px] text-neutral-800 font-mono tracking-widest uppercase text-center mt-2">
        {isStreaming ? "Real-time SSE connection active" : "Using predictive modeling for UI latency"}
      </p>
    </div>
  );
}
