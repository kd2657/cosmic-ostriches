"use client";

import { useState, useEffect } from "react";

type BootStatus = {
  ready: boolean;
  stage: number;
  total_stages: number;
  label: string;
  pct: number;
  error: string | null;
};

export default function SystemSplash({ onReady }: { onReady: () => void }) {
  const [status, setStatus] = useState<BootStatus | null>(null);
  const [displayPct, setDisplayPct] = useState(5);
  const [fadeOut, setFadeOut] = useState(false);
  const [dots, setDots] = useState("");

  // Simple dots animation for the loading text
  useEffect(() => {
    const interval = setInterval(() => {
      setDots((prev) => (prev.length >= 3 ? "" : prev + "."));
    }, 500);
    return () => clearInterval(interval);
  }, []);

  // Poll /api/status
  useEffect(() => {
    let interval: NodeJS.Timeout;
    let aborted = false;

    const poll = async () => {
      try {
        const res = await fetch("http://localhost:8000/api/status");
        if (!res.ok) throw new Error("Offline");
        const data: BootStatus = await res.json();
        if (aborted) return;
        setStatus(data);

        if (data.ready) {
          // Finish line
          setDisplayPct(100);
          setTimeout(() => setFadeOut(true), 600);
          setTimeout(() => onReady(), 1300);
        }
      } catch (e) {
        // Silent poll while backend starts
      }
    };

    interval = setInterval(poll, 700);
    poll();

    return () => {
      aborted = true;
      clearInterval(interval);
    };
  }, [onReady]);

  // Smooth percentage interpolation
  useEffect(() => {
    if (!status) return;
    const target = status.pct;
    const interval = setInterval(() => {
      setDisplayPct((prev) => {
        if (prev >= target) return target;
        return Math.min(target, prev + 1);
      });
    }, 30);
    return () => clearInterval(interval);
  }, [status?.pct]);

  return (
    <div
      className={`fixed inset-0 z-[100] flex flex-col items-center justify-center bg-neutral-950 transition-all duration-1000 ease-in-out ${
        fadeOut ? "opacity-0 scale-105 pointer-events-none" : "opacity-100 scale-100"
      }`}
    >
      {/* Background radial glow */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] bg-blue-600/5 blur-[120px] rounded-full pointer-events-none" />

      <div className="relative flex flex-col items-center gap-12 w-full max-w-md">
        {/* The "Aura Ring" - Minimalist Loader */}
        <div className="relative w-40 h-40 flex items-center justify-center">
          {/* Static Track */}
          <div className="absolute inset-0 rounded-full border-[1px] border-neutral-900" />
          
          {/* Animated Glow Ring */}
          <div 
            className="absolute inset-0 rounded-full border-[1.5px] border-transparent border-t-blue-500 transition-all duration-500"
            style={{ 
              transform: `rotate(${displayPct * 3.6}deg)`,
              filter: 'drop-shadow(0 0 8px rgba(59, 130, 246, 0.5))'
            }}
          />
          
          {/* Inner breathing circle */}
          <div className="w-32 h-32 rounded-full bg-neutral-900/40 flex items-center justify-center backdrop-blur-sm">
            <span className="text-3xl font-light tracking-tighter text-white font-mono transition-all duration-500">
              {displayPct}<span className="text-sm text-neutral-500 ml-0.5">%</span>
            </span>
          </div>

          {/* Pulse effect */}
          <div className="absolute inset-0 rounded-full border border-blue-500/20 animate-ping opacity-20" />
        </div>

        {/* Branding & Status */}
        <div className="text-center space-y-4">
          <div className="space-y-1">
            <h1 className="text-2xl font-light tracking-[0.4em] text-white uppercase font-sans">
              The Local Minima
            </h1>
            <div className="h-px w-12 bg-blue-500/30 mx-auto" />
          </div>

          <div className="h-6">
            <p className="text-[10px] text-neutral-500 font-mono tracking-[0.2em] uppercase transition-all duration-500">
              {status?.label ? `${status.label}${dots}` : `Initializing Vector Engine${dots}`}
            </p>
          </div>
        </div>
      </div>

      {/* Version footprint */}
      <div className="absolute bottom-8 text-[9px] font-mono text-neutral-800 tracking-widest uppercase">
        WELCOME TO THE LOCAL MINIMA
      </div>
    </div>
  );
}
