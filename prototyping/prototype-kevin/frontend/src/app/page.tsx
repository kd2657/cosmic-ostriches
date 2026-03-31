"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { Search, Loader2, BarChart2 } from "lucide-react";

function BackgroundBlobs() {
  const blobRefs = useRef<(HTMLDivElement | null)[]>([]);
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

    const currentPositions = blobs.map(b => ({ x: b.cx * window.innerWidth, y: b.cy * window.innerHeight }));

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
  const [articles, setArticles] = useState<any[]>([]);
  const [searchedQuery, setSearchedQuery] = useState("");
  const [isOfflineCache, setIsOfflineCache] = useState(false);
  const [backendReady, setBackendReady] = useState(false);
  const router = useRouter();

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const res = await fetch("http://localhost:8000/health");
        if (res.ok) {
          setBackendReady(true);
        } else {
          setTimeout(checkHealth, 1000);
        }
      } catch (e) {
        setTimeout(checkHealth, 1000);
      }
    };
    checkHealth();
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
        body: JSON.stringify({ query })
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
      <BackgroundBlobs />

      {isOfflineCache && (
        <div className="absolute top-4 left-1/2 -translate-x-1/2 z-50 animate-in slide-in-from-top-4 fade-in duration-400">
          <div className="bg-yellow-950 border border-yellow-700 text-yellow-500 px-4 py-2 rounded-full shadow-2xl text-sm flex items-center gap-3 whitespace-nowrap font-medium pointer-events-auto">
            <span className="flex h-2 w-2 rounded-full bg-yellow-500 animate-pulse shrink-0 shadow-[0_0_8px_rgba(234,179,8,1)]"></span>
            NewsAPI Limit Reached. Displaying locally cached vector-matches.
          </div>
        </div>
      )}

      <div className={`z-10 w-full max-w-3xl text-center space-y-8 transition-all duration-500 ${articles.length > 0 ? 'mt-0' : 'mt-[20vh]'}`}>
        <h1 className="text-5xl md:text-7xl font-extrabold tracking-tight text-white mb-4">
          The Local <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-purple-500">Minima</span>
        </h1>
        {articles.length === 0 && (
          <p className="text-lg text-neutral-400 max-w-xl mx-auto">
            Enter a topic and uncover the narratives across today's news.
          </p>
        )}

        <form onSubmit={handleSearch} className="relative mt-8 w-full mx-auto">
          <div className="relative flex items-center">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={backendReady ? "e.g. Artificial Intelligence, Global Economy..." : "Warming up AI vector models..."}
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
        
        {articles.length > 0 && (
          <div className="mt-8 flex justify-center animate-in fade-in slide-in-from-bottom-4 duration-700">
            <button
               onClick={() => router.push(`/cluster?q=${encodeURIComponent(searchedQuery)}`)}
               className="px-8 py-3 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 text-white font-bold rounded-xl shadow-lg transition-transform hover:scale-105 flex items-center gap-2 cursor-pointer"
            >
               <BarChart2 className="w-5 h-5" />
               Cluster Narratives
            </button>
          </div>
        )}
      </div>

      {articles.length > 0 && (
        <div className="z-10 w-full max-w-3xl mt-12 space-y-4 pb-20 animate-in fade-in duration-500">
          <h2 className="text-2xl font-bold text-white mb-6 border-b border-neutral-800 pb-2 flex justify-between items-end">
            <span>Fetched Articles</span>
            <span className="text-sm font-normal text-neutral-500">{articles.length} Results</span>
          </h2>
          
          <div className="grid gap-4">
            {articles.map((a: any, i: number) => (
              <div key={i} className="bg-neutral-900/60 border border-neutral-800 rounded-xl p-5 hover:bg-neutral-800/80 transition-colors backdrop-blur-md">
                <div className="flex justify-between items-start gap-4 mb-3">
                  <h3 className="text-lg font-semibold text-neutral-100 leading-tight">
                    {a.title}
                  </h3>
                  <div className="flex-shrink-0 bg-neutral-800 border border-neutral-700 text-blue-400 text-xs font-bold px-2 py-1 rounded-md whitespace-nowrap shadow-sm">
                    {a.match_score}% Match
                  </div>
                </div>
                <p className="text-neutral-400 text-sm mb-3 line-clamp-3">{a.description}</p>
                <div className="text-xs text-neutral-500 uppercase flex flex-wrap items-center gap-2">
                   <span className="font-bold text-neutral-300 bg-neutral-800 px-2 py-0.5 rounded-sm">{a.source}</span>
                   {a.publish_date && <span>• {new Date(a.publish_date).toLocaleDateString()}</span>}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
