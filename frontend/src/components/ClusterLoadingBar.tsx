"use client";

import { useState, useEffect, useRef } from "react";

const STAGES = [
  { label: "Ingesting live news feeds", icon: "📡", duration: 2200 },
  { label: "Embedding discourse vectors", icon: "🧬", duration: 2000 },
  { label: "Computing structural clusters", icon: "🔮", duration: 1800 },
  { label: "Generating AI narrative synthesis", icon: "✨", duration: 3000 },
];

export default function ClusterLoadingBar() {
  const [activeStage, setActiveStage] = useState(0);
  const [stagePct, setStagePct] = useState(0);
  const [globalPct, setGlobalPct] = useState(0);
  const startTimeRef = useRef(Date.now());
  const stageStartRef = useRef(Date.now());

  useEffect(() => {
    startTimeRef.current = Date.now();
    stageStartRef.current = Date.now();
  }, []);

  useEffect(() => {
    const interval = setInterval(() => {
      const stage = STAGES[activeStage];
      if (!stage) return;

      const elapsed = Date.now() - stageStartRef.current;
      const pct = Math.min(100, (elapsed / stage.duration) * 100);
      setStagePct(pct);

      // Global percentage calculation
      const stageWeight = 100 / STAGES.length;
      const completedPct = activeStage * stageWeight;
      const currentStagePct = (pct / 100) * stageWeight;
      setGlobalPct(Math.min(95, completedPct + currentStagePct)); // Cap at 95% until real data arrives

      if (pct >= 100 && activeStage < STAGES.length - 1) {
        setActiveStage(prev => prev + 1);
        stageStartRef.current = Date.now();
        setStagePct(0);
      }
    }, 50);

    return () => clearInterval(interval);
  }, [activeStage]);

  return (
    <div className="flex flex-col items-center justify-center gap-6 px-6 py-10 max-w-lg mx-auto">
      {/* Pulsing title */}
      <div className="text-center space-y-2">
        <h2 className="text-xl font-bold text-white font-mono tracking-tight">
          Narrative Synthesis
        </h2>
        <p className="text-xs text-neutral-600 font-mono tracking-widest uppercase">
          Processing discourse vectors
        </p>
      </div>

      {/* Main progress bar */}
      <div className="w-full space-y-2">
        <div className="relative w-full h-2 bg-neutral-900 rounded-full overflow-hidden border border-neutral-800/60">
          <div
            className="absolute inset-y-0 left-0 rounded-full transition-all duration-150 ease-out"
            style={{
              width: `${globalPct}%`,
              background: "linear-gradient(90deg, #6366f1, #8b5cf6, #a78bfa)",
              boxShadow: "0 0 15px rgba(139, 92, 246, 0.4), 0 0 40px rgba(139, 92, 246, 0.15)",
            }}
          />
        </div>
        <div className="flex justify-between items-center text-[10px] font-mono">
          <span className="text-neutral-600">STAGE {activeStage + 1}/{STAGES.length}</span>
          <span className="text-indigo-400 font-bold tabular-nums">{Math.round(globalPct)}%</span>
        </div>
      </div>

      {/* Stage list */}
      <div className="w-full space-y-2.5">
        {STAGES.map((stage, i) => {
          const isActive = i === activeStage;
          const isComplete = i < activeStage;
          const isPending = i > activeStage;

          return (
            <div
              key={i}
              className={`flex items-center gap-3 px-4 py-2.5 rounded-lg border transition-all duration-300 font-mono text-xs ${
                isActive
                  ? "bg-indigo-950/30 border-indigo-800/50 text-indigo-300 shadow-sm shadow-indigo-950/50"
                  : isComplete
                    ? "bg-neutral-900/30 border-neutral-800/30 text-green-500/70"
                    : "bg-transparent border-neutral-900/30 text-neutral-700"
              }`}
            >
              <span className="text-base w-6 text-center shrink-0">
                {isComplete ? "✓" : isActive ? stage.icon : "○"}
              </span>
              <span className={`flex-grow truncate ${isActive ? "font-medium" : ""}`}>
                {stage.label}
              </span>
              {isActive && (
                <span className="text-indigo-400/70 tabular-nums font-bold shrink-0">
                  {Math.round(stagePct)}%
                </span>
              )}
              {isComplete && (
                <span className="text-green-600/50 shrink-0">done</span>
              )}
            </div>
          );
        })}
      </div>

      {/* Subtle spinner */}
      <div className="flex items-center gap-2 text-neutral-700 text-[10px] font-mono animate-pulse mt-2">
        <div className="w-3 h-3 border-2 border-neutral-700 border-t-indigo-500 rounded-full animate-spin" />
        <span>awaiting backend response...</span>
      </div>
    </div>
  );
}
