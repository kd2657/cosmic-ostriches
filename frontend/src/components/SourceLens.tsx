"use client";

import { useState, useEffect, useMemo } from "react";
import { Newspaper, Eye, ShieldAlert, BarChart3, AlertCircle } from "lucide-react";
import SourceLensLoading from "./SourceLensLoading";

type ArticlePreview = {
  id: string;
  title: string;
  url: string;
  category: string;
  publish_date: string;
  sentiment?: any;
};

type SourceData = {
  count: number;
  divergence: number;
  articles: ArticlePreview[];
};

type SourceAnalysisResponse = {
  sources: Record<string, SourceData>;
};

type SourceLensProps = {
  query: string;
  localMode: boolean;
};


export default function SourceLens({ query, localMode }: SourceLensProps) {
  const [data, setData] = useState<SourceAnalysisResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!query) return;

    const fetchAnalysis = async () => {
      setLoading(true);
      setError(null);
      setData(null);
      try {
        const res = await fetch("http://localhost:8000/api/source-analysis", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ query, force_local: localMode })
        });
        
        if (!res.ok) throw new Error("Failed to fetch source analysis");
        
        const json = await res.json();
        setData(json.results);
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchAnalysis();
  }, [query, localMode]);

  const processedSources = useMemo(() => {
    if (!data || !data.sources || Object.keys(data.sources).length === 0) return [];

    const sourceEntries = Object.entries(data.sources).filter(([name]) => name.trim().length > 0 && name !== "Unknown Source");
    
    let maxDiv = 0.001;
    let minDiv = Number.MAX_VALUE;
    sourceEntries.forEach(([, sd]) => {
      if (sd.divergence > maxDiv) maxDiv = sd.divergence;
      if (sd.divergence < minDiv) minDiv = sd.divergence;
    });

    const range = maxDiv - minDiv || 1;

    return sourceEntries.map(([name, sd]) => {
      // Min-Max scaling stretches the scores nicely between 0.0 (Central) and 1.0 (Distinctive)
      const normalizedScore = Math.max(0, Math.min(1.0, (sd.divergence - minDiv) / range));
      
      let styleLabel: "Central" | "Balanced" | "Distinctive" = "Distinctive";
      if (normalizedScore < 0.33) styleLabel = "Central";
      else if (normalizedScore < 0.66) styleLabel = "Balanced";

      let confidence: "Low" | "Medium" | "High" = "High";
      if (sd.count <= 2) confidence = "Low";
      else if (sd.count <= 5) confidence = "Medium";

      return {
        name,
        count: sd.count,
        divergence: sd.divergence,
        normalizedScore,
        styleLabel,
        confidence,
        topArticle: sd.articles.length > 0 ? sd.articles[0] : null
      };
    }).sort((a, b) => b.count - a.count); // Sort by volume by default
  }, [data]);

  if (!query) return null;

  if (loading) return <SourceLensLoading />;

  if (error) {
    return (
      <div className="w-full max-w-3xl mx-auto text-center text-red-400 bg-red-950/20 border border-red-900 rounded-2xl p-8 z-10 relative mt-8">
        <AlertCircle className="w-8 h-8 mx-auto mb-3 text-red-500" />
        <p className="font-semibold">{error}</p>
      </div>
    );
  }

  if (processedSources.length === 0) {
    return (
      <div className="w-full max-w-3xl mx-auto text-center text-neutral-400 p-8 bg-neutral-900/40 border border-neutral-800 rounded-2xl z-10 relative mt-8">
        No source-level data could be extracted for this topic.
      </div>
    );
  }

  const totalArticles = processedSources.reduce((sum, s) => sum + s.count, 0);
  const mostDistinctive = [...processedSources].sort((a, b) => b.divergence - a.divergence)[0];

  return (
    <div className="w-full max-w-6xl mx-auto flex flex-col gap-8 animate-in fade-in duration-700 mt-8 z-10 relative">
      {/* Overview Panel */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-neutral-900/60 border border-neutral-800 rounded-2xl p-5 backdrop-blur-md flex flex-col items-center justify-center text-center">
          <Newspaper className="w-6 h-6 text-blue-400 mb-2" />
          <span className="text-3xl font-black text-white">{processedSources.length}</span>
          <span className="text-xs text-neutral-500 uppercase font-bold mt-1">Unique Sources</span>
        </div>
        <div className="bg-neutral-900/60 border border-neutral-800 rounded-2xl p-5 backdrop-blur-md flex flex-col items-center justify-center text-center">
          <BarChart3 className="w-6 h-6 text-purple-400 mb-2" />
          <span className="text-3xl font-black text-white">{totalArticles}</span>
          <span className="text-xs text-neutral-500 uppercase font-bold mt-1">Articles Analyzed</span>
        </div>
        <div className="bg-neutral-900/60 border border-neutral-800 rounded-2xl p-5 backdrop-blur-md flex flex-col items-center justify-center text-center">
          <Eye className="w-6 h-6 text-emerald-400 mb-2" />
          <span className="text-xl font-bold text-white truncate w-full px-2">{processedSources[0].name}</span>
          <span className="text-xs text-neutral-500 uppercase font-bold mt-1">Most Vocal</span>
        </div>
        <div className="bg-neutral-900/60 border border-neutral-800 rounded-2xl p-5 backdrop-blur-md flex flex-col items-center justify-center text-center">
          <ShieldAlert className="w-6 h-6 text-rose-400 mb-2" />
          <span className="text-xl font-bold text-white truncate w-full px-2">{mostDistinctive.name}</span>
          <span className="text-xs text-neutral-500 uppercase font-bold mt-1">Most Distinctive</span>
        </div>
      </div>

      <div className="mb-2 mt-4 px-2">
        <h2 className="text-2xl font-bold text-white tracking-tight">Source Narrative Lens</h2>
        <p className="text-neutral-400 text-sm mt-1">
          Displays participating outlets and how far their narrative vector deviates from the aggregate mainstream average.
        </p>
      </div>

      {/* Source Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 pb-20">
        {processedSources.map((source, idx) => (
          <div key={idx} className="bg-neutral-900/50 border border-neutral-800 rounded-2xl p-6 hover:bg-neutral-800/60 transition-colors backdrop-blur-md flex flex-col group">
            
            <div className="flex justify-between items-start mb-4">
              <div>
                <h3 className="text-xl font-bold text-white leading-tight group-hover:text-purple-400 transition-colors">{source.name}</h3>
                <div className="text-xs text-neutral-500 font-medium mt-1">
                  {source.count} Article{source.count > 1 ? 's' : ''}
                </div>
              </div>
              <div className={`px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider border ${
                source.styleLabel === 'Central' ? 'bg-blue-950/50 text-blue-300 border-blue-900' : 
                source.styleLabel === 'Balanced' ? 'bg-indigo-950/50 text-indigo-300 border-indigo-900' : 
                'bg-rose-950/50 text-rose-300 border-rose-900'
              }`}>
                {source.styleLabel}
              </div>
            </div>

            {/* Distinctiveness Bar */}
            <div className="mb-6">
              <div className="flex justify-between text-[10px] font-bold uppercase text-neutral-500 mb-1.5">
                <span>Central</span>
                <span>Distinctive</span>
              </div>
              <div className="h-2 w-full bg-neutral-950 rounded-full overflow-hidden relative border border-neutral-800">
                 {/* Background Gradient connecting Central to Distinctive */}
                 <div className="absolute inset-0 bg-gradient-to-r from-blue-500/20 via-indigo-500/20 to-rose-500/20" />
                 {/* The Indicator Dot */}
                 <div 
                   className="absolute top-0 h-full w-2 bg-white rounded-full shadow-[0_0_8px_rgba(255,255,255,0.8)] transition-all duration-1000 ease-out z-10"
                   style={{ left: `calc(${source.normalizedScore * 100}% - 4px)` }}
                 />
                 {/* Progress Fill */}
                 <div 
                   className="absolute top-0 left-0 h-full bg-gradient-to-r from-blue-500 via-indigo-500 to-rose-500 opacity-60"
                   style={{ width: `${source.normalizedScore * 100}%` }}
                 />
              </div>
              <div className="text-right mt-1.5 text-[10px] text-neutral-600 font-mono">
                Div Score: {source.divergence.toFixed(3)}
              </div>
            </div>


            {/* Representative Article */}
            {source.topArticle && (
              <div className="mt-auto pt-4 border-t border-neutral-800/60">
                <div className="text-[10px] font-bold uppercase text-neutral-500 mb-1.5">Representative Article</div>
                <a href={source.topArticle.url} target="_blank" rel="noopener noreferrer" className="text-sm font-medium text-neutral-300 line-clamp-2 hover:text-blue-400 transition-colors leading-snug">
                  "{source.topArticle.title}"
                </a>
              </div>
            )}

          </div>
        ))}
      </div>
    </div>
  );
}
