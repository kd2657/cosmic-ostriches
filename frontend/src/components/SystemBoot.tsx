"use client";

import { useState, useEffect, useRef } from "react";

type BootStatus = {
  ready: boolean;
  stage: number;
  total_stages: number;
  label: string;
  pct: number;
  error: string | null;
};

type LogEntry = {
  text: string;
  type: "info" | "success" | "error" | "system";
  timestamp: string;
};

function getTimestamp(): string {
  const now = new Date();
  return now.toTimeString().split(" ")[0] + "." + String(now.getMilliseconds()).padStart(3, "0");
}

export default function SystemBoot({ onReady }: { onReady: () => void }) {
  const [status, setStatus] = useState<BootStatus | null>(null);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [displayPct, setDisplayPct] = useState(0);
  const [fadeOut, setFadeOut] = useState(false);
  const logEndRef = useRef<HTMLDivElement>(null);
  const prevStageRef = useRef(-1);
  const readyTriggeredRef = useRef(false);

  // Seed initial log entries client-side only to prevent hydration mismatch
  useEffect(() => {
    setLogs([
      { text: "SYSTEM BOOT SEQUENCE INITIATED", type: "system", timestamp: getTimestamp() },
      { text: "Connecting to backend runtime...", type: "info", timestamp: getTimestamp() },
    ]);
  }, []);

  // Poll /api/status
  useEffect(() => {
    let interval: NodeJS.Timeout;
    let aborted = false;

    const poll = async () => {
      try {
        const res = await fetch("http://localhost:8000/api/status");
        if (!res.ok) throw new Error("Backend not responding");
        const data: BootStatus = await res.json();
        if (aborted) return;
        setStatus(data);

        // Inject log lines for new stages
        if (data.stage > prevStageRef.current) {
          const newLogs: LogEntry[] = [];
          // If we went from -1 to current, inject intermediates
          for (let i = prevStageRef.current + 1; i <= data.stage; i++) {
            if (i > 0 && prevStageRef.current >= 0) {
              newLogs.push({ text: `Stage ${i} completed ✓`, type: "success", timestamp: getTimestamp() });
            }
            if (i < data.total_stages) {
              newLogs.push({ text: data.label, type: "info", timestamp: getTimestamp() });
            }
          }
          if (newLogs.length > 0) {
            setLogs(prev => [...prev, ...newLogs]);
          }
          prevStageRef.current = data.stage;
        }

        if (data.ready && !readyTriggeredRef.current) {
          readyTriggeredRef.current = true;
          setLogs(prev => [
            ...prev,
            { text: "ALL SYSTEMS NOMINAL — VECTOR ENGINE ONLINE", type: "system", timestamp: getTimestamp() },
          ]);
          // Brief delay for user to see the final message, then fade
          setTimeout(() => setFadeOut(true), 800);
          setTimeout(() => onReady(), 1500);
        }

        if (data.error) {
          setLogs(prev => [
            ...prev,
            { text: `FATAL: ${data.error}`, type: "error", timestamp: getTimestamp() },
          ]);
        }
      } catch {
        // Backend not up yet — keep polling silently
      }
    };

    interval = setInterval(poll, 600);
    poll(); // immediate first call

    return () => {
      aborted = true;
      clearInterval(interval);
    };
  }, [onReady]);

  // Smoothly animate displayed percentage toward the real percentage
  useEffect(() => {
    if (!status) return;
    const target = status.pct;
    const step = () => {
      setDisplayPct(prev => {
        if (prev >= target) return target;
        return Math.min(target, prev + 1);
      });
    };
    const interval = setInterval(step, 20);
    return () => clearInterval(interval);
  }, [status?.pct]);

  // Auto-scroll logs
  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  return (
    <div
      className={`fixed inset-0 z-[100] flex items-center justify-center bg-neutral-950 transition-opacity duration-700 ${fadeOut ? "opacity-0 pointer-events-none" : "opacity-100"}`}
    >
      {/* Scanline overlay */}
      <div
        className="absolute inset-0 pointer-events-none z-10 opacity-[0.03]"
        style={{
          backgroundImage:
            "repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(255,255,255,0.05) 2px, rgba(255,255,255,0.05) 4px)",
        }}
      />

      {/* Glow pulser */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] rounded-full bg-blue-600/5 blur-[120px] animate-pulse pointer-events-none" />

      <div className="relative z-20 w-full max-w-2xl mx-4 flex flex-col items-center gap-8">
        {/* Title */}
        <div className="text-center space-y-2">
          <h1 className="text-4xl md:text-5xl font-extrabold tracking-tighter text-white font-mono">
            THE LOCAL{" "}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-cyan-400">
              MINIMA
            </span>
          </h1>
          <p className="text-xs tracking-[0.35em] text-neutral-600 uppercase font-mono">
            Neural Inference Engine v3.0
          </p>
        </div>

        {/* Terminal window */}
        <div className="w-full bg-neutral-900/80 border border-neutral-800 rounded-xl overflow-hidden backdrop-blur-md shadow-2xl shadow-blue-950/20">
          {/* Title bar */}
          <div className="flex items-center gap-2 px-4 py-2.5 bg-neutral-900 border-b border-neutral-800">
            <div className="flex gap-1.5">
              <span className="w-3 h-3 rounded-full bg-red-500/60" />
              <span className="w-3 h-3 rounded-full bg-yellow-500/60" />
              <span className="w-3 h-3 rounded-full bg-green-500/60" />
            </div>
            <span className="text-[10px] font-mono text-neutral-500 ml-2">boot_sequence.sh — system</span>
          </div>

          {/* Log output */}
          <div className="px-4 py-3 h-48 overflow-y-auto font-mono text-xs leading-relaxed styled-scrollbar">
            {logs.map((log, i) => (
              <div key={i} className="flex gap-2 animate-in fade-in slide-in-from-left-2 duration-300">
                <span className="text-neutral-700 shrink-0 select-none">[{log.timestamp}]</span>
                <span
                  className={
                    log.type === "system"
                      ? "text-cyan-400 font-bold"
                      : log.type === "success"
                        ? "text-green-400"
                        : log.type === "error"
                          ? "text-red-400 font-bold"
                          : "text-neutral-400"
                  }
                >
                  {log.type === "system" ? "▓▓ " : log.type === "success" ? "✓  " : log.type === "error" ? "✗  " : "→  "}
                  {log.text}
                </span>
              </div>
            ))}
            <div ref={logEndRef} />
          </div>
        </div>

        {/* Progress bar */}
        <div className="w-full space-y-3">
          <div className="flex items-center justify-between text-xs font-mono">
            <span className="text-neutral-500">
              {status ? `STAGE ${Math.min(status.stage + 1, status.total_stages)}/${status.total_stages}` : "CONNECTING..."}
            </span>
            <span className="text-blue-400 font-bold tabular-nums">{displayPct}%</span>
          </div>

          {/* Bar track */}
          <div className="relative w-full h-2.5 bg-neutral-900 rounded-full overflow-hidden border border-neutral-800">
            {/* Fill */}
            <div
              className="absolute inset-y-0 left-0 rounded-full transition-all duration-300 ease-out"
              style={{
                width: `${displayPct}%`,
                background: "linear-gradient(90deg, #0ea5e9, #06b6d4, #22d3ee)",
                boxShadow: "0 0 20px rgba(6, 182, 212, 0.5), 0 0 60px rgba(6, 182, 212, 0.2)",
              }}
            />
            {/* Shimmer */}
            <div
              className="absolute inset-0 rounded-full"
              style={{
                background:
                  "linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.1) 50%, transparent 100%)",
                animation: "shimmer 2s ease-in-out infinite",
              }}
            />
          </div>

          {/* Current stage label */}
          <p className="text-[11px] text-neutral-600 font-mono text-center truncate">
            {status?.label || "Establishing connection to inference runtime..."}
          </p>
        </div>
      </div>

      <style jsx>{`
        @keyframes shimmer {
          0% { transform: translateX(-100%); }
          100% { transform: translateX(200%); }
        }
      `}</style>
    </div>
  );
}
