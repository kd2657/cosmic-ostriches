"use client";

import { useState, useEffect } from "react";
import { Loader2, ChevronDown, ChevronUp, Link as LinkIcon, Compass } from "lucide-react";

export default function DailyGradient({ localMode = false }: { localMode?: boolean }) {
  const [gradient, setGradient] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [expandedIndex, setExpandedIndex] = useState<number | null>(null);

  useEffect(() => {
    async function loadGradient() {
      try {
        const res = await fetch(`http://localhost:8000/api/daily-gradient?force_local=${localMode}`);
        if (!res.ok) throw new Error("Failed to fetch daily gradient");
        const json = await res.json();
        setGradient(json.results || []);
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }
    setLoading(true);
    loadGradient();
  }, [localMode]);

  if (loading) {
     return (
       <div className="flex flex-col items-center py-20 z-10 relative">
          <Loader2 className="w-10 h-10 animate-spin text-blue-500 mb-4" /> 
          <p className="text-neutral-400 animate-pulse">Curating the Daily Gradient...</p>
       </div>
     );
  }

  if (error) {
     return <div className="text-red-400 py-10 text-center bg-red-950/20 border border-red-900 rounded-xl max-w-2xl mx-auto relative z-10">{error}</div>;
  }

  return (
    <div className="w-full max-w-5xl mx-auto z-10 relative animate-in fade-in duration-700 mt-8">
       <div className="mb-10 text-center space-y-4">
          <h2 className="text-4xl font-extrabold text-white flex items-center justify-center gap-3">
             <Compass className="w-8 h-8 text-blue-400" />
             Daily Gradient
          </h2>
          <p className="text-neutral-400 max-w-3xl mx-auto">
             Diverse narratives from the last 24 hours in a bite-sized serving! Expand nodes to see different perspectives.
          </p>
       </div>
       
       <div className="flex flex-col gap-6 pb-20">
         {gradient.map((item, idx) => {
            const isExpanded = expandedIndex === idx;
            const main = item.main_article;
            const subs = item.related_articles;

            return (
               <div key={idx} className={`bg-neutral-900/60 border ${isExpanded ? 'border-blue-500/50 shadow-[0_0_30px_rgba(59,130,246,0.15)]' : 'border-neutral-800'} rounded-2xl overflow-hidden transition-all duration-300 backdrop-blur-md`}>
                 <div 
                    className="p-6 cursor-pointer group hover:bg-neutral-800/80 transition-colors relative"
                    onClick={() => setExpandedIndex(isExpanded ? null : idx)}
                 >
                    <div className="flex justify-between items-start gap-4">
                       <h3 className="text-2xl font-bold text-neutral-100 leading-tight group-hover:text-blue-300 transition-colors">
                         {main.title}
                       </h3>
                       <div className="text-neutral-500 mt-1">
                          {isExpanded ? <ChevronUp className="w-6 h-6" /> : <ChevronDown className="w-6 h-6" />}
                       </div>
                    </div>
                    <p className="text-neutral-400 mt-3 line-clamp-2 md:line-clamp-none">{(main.body || "").slice(0, 450)}...</p>
                    <div className="text-xs text-neutral-500 mt-4 flex justify-between items-center">
                       <span className="font-bold text-neutral-300 uppercase bg-neutral-800 px-2 py-1 rounded">{main.source}</span>
                       <a href={main.url} target="_blank" rel="noreferrer" className="flex items-center gap-1 text-blue-400 hover:text-blue-300 bg-blue-900/20 px-3 py-1 rounded-full transition-colors" onClick={(e) => e.stopPropagation()}>
                          <LinkIcon className="w-3 h-3" /> Read Article
                       </a>
                    </div>
                 </div>

                 {/* Accordion Expansion */}
                 <div className={`grid grid-rows-[0fr] transition-[grid-template-rows] duration-500 ease-in-out ${isExpanded ? 'grid-rows-[1fr]' : ''}`}>
                    <div className="overflow-hidden">
                       <div className="p-6 pt-0 border-t border-neutral-800/50 bg-neutral-950/40">
                          <h4 className="text-sm font-semibold text-neutral-400 my-4 tracking-wider uppercase flex items-center justify-between">
                            <span>Similar Stories:</span>
                            <span className="text-xs bg-neutral-800 px-2 py-0.5 rounded text-neutral-500">{subs.length} Selected</span>
                          </h4>
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                             {subs.map((sub: any, sIdx: number) => (
                                <a key={sIdx} href={sub.url} target="_blank" rel="noreferrer" className="block p-4 rounded-xl bg-neutral-900/50 border border-neutral-800 hover:bg-neutral-800 hover:border-neutral-700 transition-all group hover:scale-[1.02] hover:-translate-y-1">
                                   <div className="text-xs font-bold text-neutral-400 uppercase mb-2 group-hover:text-purple-400 transition-colors">{sub.source}</div>
                                   <div className="text-sm text-neutral-200 font-medium line-clamp-3 leading-snug">{sub.title}</div>
                                </a>
                             ))}
                          </div>
                          {subs.length === 0 && <p className="text-neutral-500 text-sm">No highly diverse perspectives found for this topic.</p>}
                       </div>
                    </div>
                 </div>
               </div>
            );
         })}
       </div>
    </div>
  );
}
