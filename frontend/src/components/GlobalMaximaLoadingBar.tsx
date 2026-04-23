"use client";

import { useState, useEffect, useRef } from "react";

const STAGES = [
  { label: "Fetching global news feeds", icon: "🌐", duration: 2500 },
  { label: "Vectorizing article embeddings", icon: "🧬", duration: 2200 },
  { label: "Computing cross-border divergence", icon: "📊", duration: 2800 },
  { label: "Running sentiment analysis", icon: "🎭", duration: 2400 },
];

export default function GlobalMaximaLoadingBar() {
  const [simStage, setSimStage] = useState(0);
  const [simPct, setSimPct] = useState(0);
  const [simGlobalPct, setSimGlobalPct] = useState(5);
  const [globeRotation, setGlobeRotation] = useState(0);
  const stageStartRef = useRef(Date.now());

  // Globe rotation animation
  useEffect(() => {
    const interval = setInterval(() => {
      setGlobeRotation(prev => (prev + 2) % 360);
    }, 50);
    return () => clearInterval(interval);
  }, []);

  // Stage simulation
  useEffect(() => {
    const interval = setInterval(() => {
      const stage = STAGES[simStage];
      if (!stage) return;

      const elapsed = Date.now() - stageStartRef.current;
      const pct = Math.min(100, (elapsed / stage.duration) * 100);
      setSimPct(pct);

      const stageWeight = 95 / STAGES.length; // cap at 95 so it doesn't hit 100 before data arrives
      setSimGlobalPct(Math.min(95, 5 + (simStage * stageWeight) + (pct / 100 * stageWeight)));

      if (pct >= 100 && simStage < STAGES.length - 1) {
        setSimStage(prev => prev + 1);
        stageStartRef.current = Date.now();
        setSimPct(0);
      }
    }, 50);

    return () => clearInterval(interval);
  }, [simStage]);

  const displayPct = Math.round(simGlobalPct);

  return (
    <div className="flex flex-col items-center justify-center gap-8 px-6 py-14 max-w-lg mx-auto">
      {/* Animated globe spinner */}
      <div className="relative w-24 h-24 flex items-center justify-center">
        {/* Outer ring */}
        <div className="absolute inset-0 rounded-full border border-cyan-900/40" />

        {/* Orbiting dot */}
        <div
          className="absolute w-full h-full"
          style={{ transform: `rotate(${globeRotation}deg)` }}
        >
          <div
            className="absolute top-0 left-1/2 -translate-x-1/2 -translate-y-1/2 w-2 h-2 rounded-full bg-cyan-400"
            style={{ boxShadow: "0 0 8px rgba(34, 211, 238, 0.6), 0 0 20px rgba(34, 211, 238, 0.3)" }}
          />
        </div>

        {/* Second orbiting dot (counter-rotation) */}
        <div
          className="absolute w-[85%] h-[85%]"
          style={{ transform: `rotate(${-globeRotation * 0.7 + 120}deg)` }}
        >
          <div
            className="absolute top-0 left-1/2 -translate-x-1/2 -translate-y-1/2 w-1.5 h-1.5 rounded-full bg-blue-400/60"
            style={{ boxShadow: "0 0 6px rgba(96, 165, 250, 0.4)" }}
          />
        </div>

        {/* Inner glow circle */}
        <div className="w-16 h-16 rounded-full bg-neutral-900/60 border border-cyan-900/20 flex items-center justify-center backdrop-blur-sm">
          <span className="text-2xl">{STAGES[simStage]?.icon || "🌐"}</span>
        </div>

        {/* Pulse ring */}
        <div className="absolute inset-0 rounded-full border border-cyan-500/15 animate-ping opacity-30" />
      </div>

      {/* Title */}
      <div className="text-center space-y-2">
        <h2 className="text-xl font-bold text-white font-mono tracking-tight animate-pulse">
          THE GLOBAL MAXIMA
        </h2>
        <p className="text-xs text-neutral-600 font-mono tracking-widest uppercase truncate max-w-[300px]">
          {STAGES[simStage]?.label || "Processing..."}
        </p>
      </div>

      {/* Progress bar */}
      <div className="w-full space-y-2">
        <div className="relative w-full h-2 bg-neutral-900 rounded-full overflow-hidden border border-neutral-800/60 shadow-[inset_0_1px_2px_rgba(0,0,0,0.5)]">
          <div
            className="absolute inset-y-0 left-0 rounded-full transition-all duration-500 ease-out"
            style={{
              width: `${displayPct}%`,
              background: "linear-gradient(90deg, #0ea5e9, #06b6d4, #22d3ee)",
              boxShadow: "0 0 15px rgba(6, 182, 212, 0.4), 0 0 40px rgba(6, 182, 212, 0.15)",
            }}
          />
        </div>
        <div className="flex justify-between items-center text-[10px] font-mono">
          <span className="text-neutral-600 uppercase tracking-tighter">
            Stage {simStage + 1}/{STAGES.length}
          </span>
          <span className="text-cyan-400 font-bold tabular-nums">{displayPct}%</span>
        </div>
      </div>

      {/* Stage list */}
      <div className="w-full space-y-2">
        {STAGES.map((stage, i) => {
          const isActive = i === simStage;
          const isComplete = i < simStage;

          return (
            <div
              key={i}
              className={`flex items-center gap-3 px-4 py-2 rounded-lg border transition-all duration-500 font-mono text-xs ${
                isActive
                  ? "bg-cyan-950/20 border-cyan-500/50 text-cyan-200 shadow-[0_0_20px_rgba(6,182,212,0.1)]"
                  : isComplete
                    ? "bg-neutral-900/40 border-neutral-800/40 text-neutral-500"
                    : "bg-transparent border-neutral-900/30 text-neutral-800"
              }`}
            >
              <div className="w-5 h-5 flex items-center justify-center shrink-0">
                {isComplete ? (
                  <span className="text-cyan-500">✓</span>
                ) : isActive ? (
                  <div className="w-2 h-2 bg-cyan-500 rounded-full animate-ping" />
                ) : (
                  <div className="w-1.5 h-1.5 bg-neutral-800 rounded-full" />
                )}
              </div>
              <span className={`flex-grow truncate ${isActive ? "font-medium" : ""}`}>
                {stage.label}
              </span>
              {isActive && (
                <div className="flex space-x-0.5">
                  {[1, 2, 3].map(d => (
                    <div
                      key={d}
                      className="w-0.5 h-1.5 bg-cyan-500 animate-pulse"
                      style={{ animationDelay: `${d * 200}ms` }}
                    />
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>

      <p className="text-[9px] text-neutral-800 font-mono tracking-widest uppercase text-center mt-2">
        Analyzing global narratives...
      </p>
    </div>
  );
}
