"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { Search, Loader2, BarChart2, Compass, Layers, Database, WifiOff, Globe, Link as LinkIcon } from "lucide-react";
import DailyGradient from "@/components/DailyGradient";
import GlobalMaxima from "@/components/GlobalMaxima";
import SystemSplash from "@/components/SystemSplash";
import SystemBoot from "@/components/SystemBoot";
import Tooltip from "@/components/Tooltip";

// Set this to false to use the Terminal/Cyberpunk style bootup (SystemBoot)
// ***************************
const USE_MINIMAL_BOOT = true; 
// ***************************

type ArticleSentiment = {
  label: string;
  sentiment: string;
  confidence: number;
  polarity?: number;
  scores: Record<string, number>;
};

type Article = {
  id: string;
  title: string;
  body: string;
  source?: string;
  publish_date?: string;
  url?: string;
  match_score: number;
  sentiment?: ArticleSentiment | null;
};

const sentimentBadgeStyles: Record<string, string> = {
  positive: "bg-emerald-950/70 text-emerald-300 border-emerald-800",
  slightly_positive: "bg-lime-950/70 text-lime-300 border-lime-800",
  slightly_negative: "bg-rose-950/70 text-rose-300 border-rose-800",
  negative: "bg-red-950/70 text-red-300 border-red-800",
};

const getSentimentBadgeStyle = (sentiment: string) =>
  sentimentBadgeStyles[sentiment] ?? "bg-neutral-900/70 text-neutral-300 border-neutral-700";

function BackgroundBlobs() {
  const blobRefs = useRef<(HTMLDivElement | null)[]>([]);
  const vectorRefs = useRef<(HTMLDivElement | null)[]>([]);
  const maskLayerRef = useRef<HTMLDivElement | null>(null);
  const mouseRef = useRef({ x: 0, y: 0, active: false });

  useEffect(() => {
    // Safely configure window defaults inside the effect
    mouseRef.current.x = window.innerWidth / 2;
    mouseRef.current.y = window.innerHeight / 2;

    const handleMouseMove = (e: MouseEvent) => {
      mouseRef.current = { x: e.clientX, y: e.clientY, active: true };
    };
    const handleMouseLeave = () => {
      mouseRef.current.active = false;
    };
    
    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseleave", handleMouseLeave);
    window.addEventListener("blur", handleMouseLeave);
    
    let animationFrameId: number;
    const blobs = [
      { id: 1, color: "bg-blue-600/20",   cx: 0.2, cy: 0.2, r: 250, speed: 0.0010, offset: 0 },
      { id: 2, color: "bg-purple-600/20", cx: 0.8, cy: 0.8, r: 350, speed: 0.0007, offset: 2 },
      { id: 3, color: "bg-pink-600/20",   cx: 0.8, cy: 0.3, r: 200, speed: 0.0015, offset: 4 },
      { id: 4, color: "bg-teal-600/20",   cx: 0.2, cy: 0.8, r: 250, speed: 0.0011, offset: 5 },
      { id: 5, color: "bg-indigo-600/20", cx: 0.5, cy: 0.5, r: 400, speed: 0.0008, offset: 1 },
    ];
    const vectors = Array.from({ length: 40 }).map((_, i) => ({
      id: i + 1,
      cx: 0.05 + Math.random() * 0.9,
      cy: 0.05 + Math.random() * 0.9,
      speed: 0.0003 + Math.random() * 0.0005,
      offset: Math.random() * Math.PI * 2,
      text: `[${(Math.random() * 2 - 1).toFixed(3)}, ${(Math.random() * 2 - 1).toFixed(3)}]`
    }));

    vectorRefs.current.forEach((el, index) => {
       if (el && vectors[index]) {
          el.textContent = vectors[index].text;
       }
    });

    const currentPositions = blobs.map(b => ({ x: b.cx * window.innerWidth, y: b.cy * window.innerHeight }));
    const vectorPositions = vectors.map(v => ({ x: v.cx * window.innerWidth, y: v.cy * window.innerHeight }));
    
    let maskX = mouseRef.current.x;
    let maskY = mouseRef.current.y;
    let maskO = 0;

    const animate = (time: number) => {
      blobRefs.current.forEach((el, index) => {
        if (!el) return;
        const b = blobs[index];
        const w = window.innerWidth;
        const h = window.innerHeight;
        
        // Idle organic trigonometric floating trajectory
        const floatX = (b.cx * w) + Math.sin(time * b.speed + b.offset) * 150;
        const floatY = (b.cy * h) + Math.cos(time * b.speed + b.offset) * 150;
        
        let targetX = floatX;
        let targetY = floatY;

        // Dynamic Mathematical Mouse Repulsion Field (inverse distance pushing)
        if (mouseRef.current.active) {
          const dx = floatX - mouseRef.current.x;
          const dy = floatY - mouseRef.current.y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          
          if (dist < 450 && dist > 1) { 
            const force = (450 - dist) / 450; 
            const pushFactor = force * 350; // Massively aggressive distance curve away from mouse
            targetX += (dx / dist) * pushFactor;
            targetY += (dy / dist) * pushFactor;
          }
        }

        // Apply smooth linear interpolation so they glide instead of teleporting
        currentPositions[index].x += (targetX - currentPositions[index].x) * 0.04;
        currentPositions[index].y += (targetY - currentPositions[index].y) * 0.04;
        
        // Send transform instructions universally relative to document dimensions. 
        // Bypassing React's render loop saves critical frames!
        el.style.transform = `translate(${currentPositions[index].x - b.r}px, ${currentPositions[index].y - b.r}px)`;
      });

      vectorRefs.current.forEach((el, index) => {
        if (!el || !vectors[index]) return;
        const v = vectors[index];
        const w = window.innerWidth;
        const h = window.innerHeight;
        const floatX = (v.cx * w) + Math.sin(time * v.speed * 1.2 + v.offset) * 40;
        const floatY = (v.cy * h) + Math.cos(time * v.speed * 1.2 + v.offset) * 40;
        vectorPositions[index].x += (floatX - vectorPositions[index].x) * 0.02;
        vectorPositions[index].y += (floatY - vectorPositions[index].y) * 0.02;
        el.style.transform = `translate(${vectorPositions[index].x}px, ${vectorPositions[index].y}px)`;
      });

      maskX += (mouseRef.current.x - maskX) * 0.1;
      maskY += (mouseRef.current.y - maskY) * 0.1;
      maskO += ((mouseRef.current.active ? 1 : 0) - maskO) * 0.05;
      
      if (maskLayerRef.current) {
        maskLayerRef.current.style.opacity = maskO.toString();
        const maskGrad = `radial-gradient(circle 600px at ${maskX}px ${maskY}px, black 0%, transparent 100%)`;
        maskLayerRef.current.style.setProperty('-webkit-mask-image', maskGrad);
        maskLayerRef.current.style.setProperty('mask-image', maskGrad);
      }

      animationFrameId = requestAnimationFrame(animate);
    };

    animationFrameId = requestAnimationFrame(animate);
    
    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseleave", handleMouseLeave);
      window.removeEventListener("blur", handleMouseLeave);
      cancelAnimationFrame(animationFrameId);
    };
  }, []);

  return (
    <div className="fixed top-0 left-0 w-full h-full overflow-hidden z-0 pointer-events-none">
      <div ref={maskLayerRef} className="absolute inset-0 z-10 pointer-events-none transition-opacity duration-300" style={{ opacity: 0 }}>
         <div className="absolute inset-0 z-0 opacity-[0.08]" style={{ backgroundImage: 'linear-gradient(rgba(255, 255, 255, 1) 1px, transparent 1px), linear-gradient(90deg, rgba(255, 255, 255, 1) 1px, transparent 1px)', backgroundSize: '40px 40px' }} />
         {Array.from({ length: 40 }).map((_, i) => (
            <div
              key={`vec-${i}`}
              ref={(el) => {
                if (el) vectorRefs.current[i] = el;
              }}
              className="absolute top-0 left-0 text-neutral-700/60 font-mono text-[10px] sm:text-xs tracking-widest whitespace-nowrap transition-none will-change-transform font-bold"
            ></div>
         ))}
      </div>

      {[
        { id: 1, color: "bg-blue-600/20",   r: 250 },
        { id: 2, color: "bg-purple-600/20", r: 350 },
        { id: 3, color: "bg-pink-600/20",   r: 200 },
        { id: 4, color: "bg-teal-600/20",   r: 250 },
        { id: 5, color: "bg-indigo-600/20", r: 400 },
      ].map((b, i) => (
        <div 
          key={b.id}
          ref={(el) => {
            if (el) blobRefs.current[i] = el;
          }}
          className={`absolute top-0 left-0 rounded-full blur-[100px] ${b.color} transition-none will-change-transform`}
          style={{ width: b.r * 2, height: b.r * 2 }}
        />
      ))}
    </div>
  );
}

export default function Home() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [articles, setArticles] = useState<Article[]>([]);
  const [searchedQuery, setSearchedQuery] = useState("");
  const [isOfflineCache, setIsOfflineCache] = useState(false);
  const [backendReady, setBackendReady] = useState(false);
  const [showBoot, setShowBoot] = useState(true);
  const [activeTab, setActiveTab] = useState<"search" | "gradient" | "global">("search");
  const [localMode, setLocalMode] = useState(false);
  const router = useRouter();

  useEffect(() => {
    // Poll /api/status to check if models are loaded
    const checkStatus = async () => {
      try {
        const res = await fetch("http://localhost:8000/api/status");
        if (res.ok) {
          const data = await res.json();
          if (data.ready) {
            setBackendReady(true);
            return; // Stop polling
          }
        }
        setTimeout(checkStatus, 800);
      } catch (e) {
        setTimeout(checkStatus, 800);
      }
    };
    checkStatus();
  }, []);
  
  useEffect(() => {
    if (isOfflineCache) {
      const timer = setTimeout(() => setIsOfflineCache(false), 4000);
      return () => clearTimeout(timer);
    }
  }, [isOfflineCache]);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    try {
      const res = await fetch("http://localhost:8000/api/articles", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, force_local: localMode })
      });
      if (!res.ok) throw new Error("Fetch failed");
      const json = await res.json();
      setArticles(json.articles || []);
      setIsOfflineCache(json.is_offline_cache || false);
      setSearchedQuery(query);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-neutral-950 flex flex-col items-center py-20 px-4 relative overflow-hidden">
      {showBoot && (
        USE_MINIMAL_BOOT ? (
          <SystemSplash onReady={() => {
            if (!backendReady) setBackendReady(true);
            setShowBoot(false);
          }} />
        ) : (
          <SystemBoot onReady={() => {
            if (!backendReady) setBackendReady(true);
            setShowBoot(false);
          }} />
        )
      )}
      <BackgroundBlobs />

      <div className="absolute top-4 right-4 z-50 animate-in fade-in slide-in-from-top-4 duration-500">
         <Tooltip content="Local Mode disables the NewsAPI text fetcher entirely and routes search/exploration explicitly through the local ChromeDB vector embeddings.">
           <button 
              onClick={() => setLocalMode(!localMode)}
              className={`flex items-center gap-1.5 px-3 py-1 rounded-full border text-[10px] sm:text-xs font-medium transition-all shadow-md backdrop-blur-md ${localMode ? 'bg-amber-500/10 text-amber-500 border-amber-500/40 shadow-[0_0_10px_rgba(245,158,11,0.2)]' : 'bg-neutral-900/30 text-neutral-500 border-neutral-800/50 hover:text-neutral-400'}`}
           >
              {localMode ? <WifiOff className="w-3 h-3" /> : <Database className="w-3 h-3" />}
              {localMode ? "LOCAL MODE: ON" : "LOCAL MODE: OFF"}
           </button>
         </Tooltip>
      </div>

      {isOfflineCache && (
        <div className="absolute top-4 left-1/2 -translate-x-1/2 z-50 animate-in slide-in-from-top-4 fade-in duration-400">
          {localMode ? (
            <div className="bg-blue-950 border border-blue-700 text-blue-400 px-4 py-2 rounded-full shadow-2xl text-sm flex items-center gap-3 whitespace-nowrap font-medium pointer-events-auto">
              <Database className="w-4 h-4 shrink-0 shadow-[0_0_8px_rgba(59,130,246,0.5)]" />
              Local Mode Enabled. Displaying results from local database.
            </div>
          ) : (
            <div className="bg-yellow-950 border border-yellow-700 text-yellow-500 px-4 py-2 rounded-full shadow-2xl text-sm flex items-center gap-3 whitespace-nowrap font-medium pointer-events-auto">
              <span className="flex h-2 w-2 rounded-full bg-yellow-500 animate-pulse shrink-0 shadow-[0_0_8px_rgba(234,179,8,1)]"></span>
              NewsAPI Limit Reached. Displaying locally cached vector-matches.
            </div>
          )}
        </div>
      )}

      <div className={`z-10 w-full max-w-3xl text-center space-y-8 transition-all duration-500 ${articles.length > 0 || activeTab === 'gradient' || activeTab === 'global' ? 'mt-0' : 'mt-[20vh]'}`}>
        <h1 className="text-6xl md:text-8xl lg:text-[7rem] font-extrabold tracking-tighter text-white mb-6 relative group inline-block whitespace-nowrap">
          The Local{" "}
          <span className="relative inline-block text-transparent bg-clip-text bg-gradient-to-r from-blue-400 via-indigo-500 to-purple-500 transition-all duration-700 ease-out group-hover:drop-shadow-[0_0_35px_rgba(99,102,241,0.8)] group-hover:scale-[0.96] group-hover:translate-y-1">
            Minima
          </span>
        </h1>
        {articles.length === 0 && activeTab === 'search' && !searchedQuery && (
          <p className="text-lg text-neutral-400 max-w-xl mx-auto">
            Enter a topic and uncover the narratives across today's news.
          </p>
        )}

        <div className="flex justify-center gap-4 mt-8 flex-wrap slide-in-from-bottom-4 animate-in fade-in duration-500">
           <button 
              onClick={() => {
                  setActiveTab("search");
                  setQuery("");
                  setSearchedQuery("");
                  setArticles([]);
              }} 
              className={`px-6 py-2 rounded-full font-semibold transition-all flex items-center gap-2 ${activeTab === 'search' ? 'bg-white text-black shadow-[0_0_20px_rgba(255,255,255,0.2)]' : 'bg-neutral-900 border border-neutral-800 text-neutral-400 hover:text-white hover:bg-neutral-800'}`}>
              <Layers className="w-5 h-5" /> News Clusters
           </button>
           <button 
              onClick={() => {
                 setActiveTab("gradient");
                 setQuery("");
                 setSearchedQuery("");
                 setArticles([]);
              }} 
              disabled={!backendReady}
              className={`px-6 py-2 rounded-full font-semibold transition-all flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed ${activeTab === 'gradient' ? 'bg-white text-black shadow-[0_0_20px_rgba(255,255,255,0.2)]' : 'bg-neutral-900 border border-neutral-800 text-neutral-400 hover:text-white hover:bg-neutral-800'}`}
           >
              {backendReady ? <Compass className="w-5 h-5" /> : <Loader2 className="w-5 h-5 animate-spin" />} Daily Gradient
           </button>
           <button 
              onClick={() => {
                 setActiveTab("global");
                 setQuery("");
                 setSearchedQuery("");
                 setArticles([]);
              }}
              disabled={!backendReady}
              className={`px-6 py-2 rounded-full font-semibold transition-all flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed ${activeTab === 'global' ? 'bg-indigo-600 text-white shadow-[0_0_20px_rgba(79,70,229,0.4)] border-indigo-500' : 'bg-neutral-900 border border-neutral-800 text-neutral-400 hover:text-white hover:bg-neutral-800'}`}
           >
              {backendReady ? <Globe className="w-5 h-5" /> : <Loader2 className="w-5 h-5 animate-spin" />} Global Maxima
           </button>
        </div>

        {(activeTab === "search" || activeTab === "global") && (
          <form onSubmit={handleSearch} className="relative mt-8 w-full max-w-3xl mx-auto animate-in fade-in duration-500">
            <div className="relative flex items-center">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={backendReady ? (activeTab === "global" ? "Enter a topic to explore global news narratives" : "e.g. Artificial Intelligence, Global Economy...") : "Warming up AI vector models..."}
              className="w-full pl-6 pr-32 py-4 bg-neutral-900/80 border border-neutral-800 rounded-2xl text-white placeholder-neutral-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all text-lg shadow-xl backdrop-blur-sm disabled:opacity-50 disabled:cursor-not-allowed"
              disabled={loading || !backendReady}
            />
            <button
              type="submit"
              disabled={loading || !query.trim() || !backendReady}
              className="absolute right-2 px-6 py-2 bg-white text-black font-semibold rounded-xl hover:bg-neutral-200 transition-colors disabled:opacity-50 flex items-center gap-2 cursor-pointer"
            >
              {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : 
               !backendReady ? <Loader2 className="w-5 h-5 animate-spin" /> : "Search"}
            </button>
          </div>
        </form>
        )}
        
        {activeTab === "search" && articles.length > 0 && (
          <div className="mt-8 flex justify-center animate-in fade-in slide-in-from-bottom-4 duration-700">
            <button
               onClick={() => router.push(`/cluster?q=${encodeURIComponent(searchedQuery)}&local=${localMode}`)}
               className="px-8 py-3 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 text-white font-bold rounded-xl shadow-lg transition-transform hover:scale-105 flex items-center gap-2 cursor-pointer"
            >
               <BarChart2 className="w-5 h-5" />
               Cluster Narratives
            </button>
          </div>
        )}
      </div>

      {activeTab === "search" && articles.length > 0 && (
        <div className="z-10 w-full max-w-5xl mx-auto mt-12 space-y-4 pb-20 animate-in fade-in duration-500">
          <h2 className="text-2xl font-bold text-white mb-6 border-b border-neutral-800 pb-2 flex justify-between items-end">
            <span>Fetched Articles</span>
            <span className="text-sm font-normal text-neutral-500">{articles.length} Results</span>
          </h2>
          
          <div className="grid gap-4">
            {articles.map((a, i) => (
              <div key={i} className="bg-neutral-900/60 border border-neutral-800 rounded-xl p-5 hover:bg-neutral-800/80 transition-colors backdrop-blur-md">
                <div className="flex justify-between items-start gap-4 mb-3">
                  <h3 className="text-lg font-semibold text-neutral-100 leading-tight">
                    {a.title}
                  </h3>
                  <div className="flex-shrink-0 bg-neutral-800 border border-neutral-700 text-blue-400 text-xs font-bold px-2 py-1 rounded-md whitespace-nowrap shadow-sm">
                    {a.match_score}% Match
                  </div>
                </div>
                <p className="text-neutral-400 text-sm mb-3 line-clamp-3">{(a.body || "").slice(0, 300)}...</p>
                <div className="flex justify-between items-center mt-auto">
                   <div className="text-xs text-neutral-500 uppercase flex flex-wrap items-center gap-2">
                      <span className="font-bold text-neutral-300 bg-neutral-800 px-2 py-0.5 rounded-sm">{a.source}</span>
                      {a.publish_date && <span>• {new Date(a.publish_date).toLocaleDateString()}</span>}
                   </div>
                   {a.url && (
                      <a 
                        href={a.url} 
                        target="_blank" 
                        rel="noreferrer" 
                        className="flex items-center gap-1 text-blue-400 hover:text-blue-300 bg-blue-900/10 px-3 py-1 rounded-full transition-colors text-xs font-semibold"
                      >
                         <LinkIcon className="w-3 h-3" /> Read Article
                      </a>
                   )}
                </div>
                {a.sentiment && (
                  <div className="mt-4 pt-3 border-t border-neutral-800 flex items-center justify-between gap-3">
                    <span
                      className={`text-xs font-bold px-2.5 py-1 rounded-full border ${getSentimentBadgeStyle(a.sentiment.sentiment)}`}
                    >
                      {a.sentiment.label}
                    </span>
                    <span className="text-xs text-neutral-400">
                      Sentiment confidence: {(a.sentiment.confidence * 100).toFixed(1)}%
                    </span>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {activeTab === "gradient" && <DailyGradient localMode={localMode} />}
      
      {activeTab === "global" && (
         <div className="w-full mt-12 mb-20 animate-in fade-in duration-500">
            <GlobalMaxima key={searchedQuery} query={searchedQuery} localMode={localMode} />
         </div>
      )}
    </div>
  );
}
