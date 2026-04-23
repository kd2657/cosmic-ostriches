"use client";

import { useState, useEffect, useMemo, useCallback } from "react";
import dynamic from "next/dynamic";
import { Loader2, X } from "lucide-react";

// Plotly must be loaded dynamically because it requires the window object
const Plot = dynamic(() => import("react-plotly.js"), { ssr: false });

type TopArticle = {
  title: string;
  source: string;
  url: string;
};

type ArticleSentiment = {
  label: string;
  sentiment: string;
  confidence: number;
  polarity?: number;
  scores: Record<string, number>;
};

type CountryStat = {
  count: number;
  divergence: number;
  mean_sentiment: number;
  top_article: TopArticle;
  articles: Array<TopArticle & { publish_date?: string; sentiment?: ArticleSentiment | null }>;
};

type GlobalAnalysisResponse = {
  countries: Record<string, CountryStat>;
  pairwise_matrix: number[][];
  top_countries: string[];
};

type GlobalMaximaProps = {
  query: string;
  localMode: boolean;
};

// ── Plotly error handler ───────────────────────────────────────────────────
// Silently swallow all internal Plotly errors — they are handled by the
// unhandledrejection suppressor above and don't need to surface to the terminal.
function handlePlotlyError(_err: any) { /* intentionally silent */ }

const sentimentBadgeStyles: Record<string, string> = {
  positive: "bg-emerald-950/70 text-emerald-300 border-emerald-800",
  slightly_positive: "bg-lime-950/70 text-lime-300 border-lime-800",
  slightly_negative: "bg-rose-950/70 text-rose-300 border-rose-800",
  negative: "bg-red-950/70 text-red-300 border-red-800",
};

const getSentimentBadgeStyle = (sentiment: string) =>
  sentimentBadgeStyles[sentiment] ?? "bg-neutral-900/70 text-neutral-300 border-neutral-700";

export default function GlobalMaxima({ query, localMode }: GlobalMaximaProps) {
  // 1. ALL HOOKS MUST BE AT THE TOP (Before any early returns)
  const [data, setData] = useState<GlobalAnalysisResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedCountry, setSelectedCountry] = useState<string | null>(null);

  // Suppress the Plotly _scrollZoom unhandled rejection at the earliest possible stage.
  // This must be registered on mount so it is active before any Plotly renders.
  // It catches both the TypeError variant and any string-based rejections.
  useEffect(() => {
    const handler = (event: PromiseRejectionEvent) => {
      const reason = event.reason;
      const msg: string = (reason instanceof Error ? reason.message : String(reason ?? ''));
      if (msg.includes('_scrollZoom') || msg.includes("Cannot read properties of undefined (reading '_scrollZoom')")) {
        event.preventDefault();
        event.stopImmediatePropagation();
      }
    };
    // useCapture: true ensures we run before Next.js's internal reporter
    window.addEventListener('unhandledrejection', handler, true);
    return () => window.removeEventListener('unhandledrejection', handler, true);
  }, []);

  // Data fetching effect
  useEffect(() => {
    if (!query) return;

    const fetchAnalysis = async () => {
      setLoading(true);
      setError(null);
      setData(null);
      try {
        const res = await fetch("http://localhost:8000/api/global-analysis", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ query, force_local: localMode })
        });
        
        if (!res.ok) throw new Error("Failed to fetch global analysis");
        
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

  // ── Memoized Map Objects (Must handle null data gracefully) ───────────────
  const mapData = useMemo(() => {
    if (!data || Object.keys(data.countries).length === 0) return [];

    const { countries } = data;
    const locations = Object.keys(countries);
    const counts = locations.map(c => countries[c].count);
    const sentiments = locations.map(c => countries[c].mean_sentiment);
    const maxVolume = Math.max(...counts);
    const markerSizes = counts.map(count => Math.max(8, (count / maxVolume) * 40));
    const hoverTexts = locations.map(c =>
      `<b>${c}</b><br>Volume: ${countries[c].count}<br>Divergence (vs World): ${countries[c].divergence.toFixed(3)}<br><i style="font-size: 10px;">Click to view ${countries[c].count} articles</i>`
    );

    return [{
      type: 'scattergeo',
      locationmode: 'country names',
      locations,
      text: hoverTexts,
      hoverinfo: 'text',
      marker: {
        size: markerSizes,
        color: sentiments,
        colorscale: [[0, 'rgb(220,38,38)'], [0.375, 'rgb(251,113,133)'], [0.5, 'rgb(115,115,115)'], [0.625, 'rgb(163,230,53)'], [1, 'rgb(22,163,74)']],
        cmin: -1,
        cmax: 1,
        line: { color: 'rgb(30,30,30)', width: 1.5 },
        opacity: 0.85
      }
    }] as any[];
  }, [data]);

  const mapLayout = useMemo(() => ({
    geo: {
      showframe: false,
      showcoastlines: true,
      coastlinecolor: 'rgba(255,255,255,0.1)',
      projection: { type: 'equirectangular' },
      bgcolor: 'rgba(0,0,0,0)',
      showland: true,
      landcolor: 'rgba(30,30,30,0.8)',
      showocean: true,
      oceancolor: 'rgba(10,10,15,1)',
      showcountries: true,
      countrycolor: 'rgba(255,255,255,0.05)',
    },
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: 'rgba(0,0,0,0)',
    margin: { t: 0, b: 0, l: 0, r: 0 },
    hoverlabel: { bgcolor: '#171717', bordercolor: '#333', font: { color: 'white' } },
    autosize: true
  }), []);

  const commonConfig = useMemo(() => ({
    responsive: true,
    displayModeBar: false,
    scrollZoom: false
  }), []);

  // ── Memoized Heatmap Objects ──────────────────────────────────────────────
  const heatmapData = useMemo(() => {
    if (!data || !data.pairwise_matrix || data.pairwise_matrix.length === 0) return [];

    const { pairwise_matrix, top_countries } = data;
    const heatmapZ = [...pairwise_matrix].reverse();
    const heatmapY = [...top_countries].reverse();

    return [{
      z: heatmapZ,
      x: top_countries,
      y: heatmapY,
      type: 'heatmap',
      colorscale: 'Plasma',
      text: heatmapZ,
      texttemplate: '%{text:.2f}',
      textfont: { color: 'white', size: 10 },
      hoverongaps: false,
      hovertemplate: '<b>%{y} - %{x}</b><br>Distance: %{z:.3f}<extra></extra>'
    }] as any[];
  }, [data]);

  const heatmapLayout = useMemo(() => ({
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: 'rgba(0,0,0,0)',
    margin: { t: 0, b: 120, l: 120, r: 0 },
    xaxis: { tickangle: -45, color: 'white', tickfont: { size: 12 } },
    yaxis: { color: 'white', tickfont: { size: 12 }, tickpad: 8 },
    autosize: true
  }), []);

  const mapStyle = useMemo(() => ({ width: "100%", height: "100%" }), []);

  const handlePlotInitialized = useCallback((figure: any, graphDiv: any) => {
    if (graphDiv && graphDiv.on) {
      graphDiv.on('plotly_click', (e: any) => {
        if (e.points && e.points[0]) {
          const point = e.points[0] as any;
          const cname = point.location;
          if (cname) setSelectedCountry(String(cname));
        }
      });
    }
  }, []);

  // 2. CONDITIONAL RETURNS (Only after all hooks define)
  if (!query) return null;

  if (loading) {
    return (
      <div className="w-full flex flex-col items-center justify-center py-32 text-white">
        <Loader2 className="w-10 h-10 animate-spin text-blue-500 mb-4" />
        <span className="text-xl font-medium tracking-wide">Assembling Global Vectors...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="w-full text-center text-red-500 bg-red-950/20 border border-red-900 rounded-xl p-8">
        Failed to load global analysis: {error}
      </div>
    );
  }

  if (!data || Object.keys(data.countries).length === 0) {
    return (
      <div className="w-full text-center text-neutral-400 p-8 bg-neutral-900/40 rounded-xl">
        No geographic data found for the given query. Please try another topic.
      </div>
    );
  }

  const { countries, top_countries } = data;
  const maxVolume = Math.max(...Object.values(countries).map(c => c.count));

  return (
    <div className="w-full max-w-6xl mx-auto flex flex-col gap-8 animate-in fade-in duration-700">
      
      {/* MAP COMPONENT */}
      <div className="w-full bg-neutral-900/60 border border-neutral-800 rounded-3xl overflow-hidden backdrop-blur-md shadow-2xl flex flex-col pt-6">
        <div className="px-6 mb-2 z-10 w-full">
          <h2 className="text-2xl font-bold text-white tracking-tight">Geopolitical Consensus Tracker</h2>
          <p className="text-neutral-400 text-sm mt-1 max-w-full">
            Bubble size represents how many articles a country published. Color indicates the overall tone of those stories from red to green.
          </p>
        </div>
        
        <div className="w-full h-[60vh] min-h-[400px]">
          <Plot
            key={`map-${query}`}
            data={mapData}
            layout={mapLayout}
            config={commonConfig}
            style={mapStyle}
            onError={handlePlotlyError}
            onUpdate={handlePlotlyError}
            onInitialized={handlePlotInitialized}
          />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-start">
        {/* BAR CHART */}
        <div className="bg-neutral-900/60 border border-neutral-800 rounded-3xl p-6 backdrop-blur-md flex flex-col">
          <h3 className="text-lg font-bold text-white mb-2">Reporting Output</h3>
          <p className="text-sm text-neutral-400 mb-6">Top reporting countries by publisher volume.</p>
          
          <div className="flex flex-col gap-3.5 flex-grow overflow-y-auto pr-2 mt-2">
            {top_countries.map((c) => {
              const count = countries[c].count;
              const pct = (count / maxVolume) * 100;
              return (
                <div key={c} className="flex items-center gap-4 group cursor-default">
                  <span className="text-sm font-semibold text-neutral-300 w-28 truncate text-right group-hover:text-white transition-colors">
                    {c}
                  </span>
                  <div className="flex-grow flex items-center gap-3">
                    <div 
                      className="h-6 bg-blue-600/70 rounded-full shadow-sm group-hover:bg-blue-500 transition-colors" 
                      style={{ width: `${Math.max(2, pct)}%` }} 
                    />
                    <span className="text-xs font-bold text-blue-300 font-mono">{count}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* OUTLIER LIST */}
        <div className="bg-neutral-900/60 border border-neutral-800 rounded-3xl p-6 backdrop-blur-md flex flex-col">
          <h3 className="text-lg font-bold text-white mb-2">Global Divergence Outliers</h3>
          <p className="text-sm text-neutral-400 mb-6">Countries whose semantic reporting vectors differ the most from the rest of the world.</p>
          
          <div className="flex flex-col gap-3 flex-grow overflow-y-auto pr-2 mt-2">
            {Object.keys(countries)
              .sort((a, b) => countries[b].divergence - countries[a].divergence)
              .slice(0, 15)
              .map((c, i) => (
                <div key={c} className="flex items-center justify-between p-3 rounded-xl bg-neutral-800/40 border border-neutral-800/80 hover:bg-neutral-800/60 transition-colors">
                  <div className="flex items-center gap-3">
                    <span className="text-indigo-400/50 font-mono text-sm w-4">{i + 1}</span>
                    <span className="font-semibold text-neutral-200">{c}</span>
                  </div>
                  <div className="flex items-center gap-3 w-[60%] lg:w-1/2 justify-end">
                    <div className="flex-grow h-2 bg-neutral-800 rounded-full overflow-hidden shadow-inner hidden sm:block">
                      <div 
                        className="h-full bg-gradient-to-r from-blue-500 to-purple-500 rounded-full" 
                        style={{ width: `${Math.min(100, (countries[c].divergence / 1.5) * 100)}%` }}
                      />
                    </div>
                    <span className="text-xs font-mono text-indigo-300 font-bold w-12 text-right">
                      {countries[c].divergence.toFixed(3)}
                    </span>
                  </div>
                </div>
            ))}
          </div>
        </div>
      </div>

      {/* MATRIX */}
      {top_countries.length > 1 && (
        <div className="w-full bg-neutral-900/60 border border-neutral-800 rounded-3xl p-6 backdrop-blur-md mt-4">
            <h3 className="text-xl font-bold text-white mb-2">Pairwise Divergence Matrix</h3>
            <p className="text-sm text-neutral-400 mb-8 max-w-full">
              A Euclidean distance heatmap showing sematic differences between reporting countries.
            </p>
            <div className="w-full h-[600px] flex items-center justify-center">
              <Plot
                data={heatmapData}
                layout={heatmapLayout}
                config={commonConfig}
                style={{ width: "100%", height: "100%" }}
                onError={handlePlotlyError}
              />
            </div>
        </div>
      )}

      {/* MODAL */}
      {selectedCountry && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in">
          <div className="w-full max-w-2xl max-h-[85vh] bg-neutral-900 border border-neutral-800 rounded-2xl shadow-2xl flex flex-col overflow-hidden">
            <div className="px-6 py-5 border-b border-neutral-800 flex items-center justify-between shrink-0 bg-neutral-900/90">
              <div>
                <h3 className="text-2xl font-bold text-white">{selectedCountry}</h3>
                <p className="text-neutral-400 text-sm">{countries[selectedCountry].count} articles tracked</p>
              </div>
              <button onClick={() => setSelectedCountry(null)} className="p-2 bg-neutral-800 text-neutral-400 rounded-full hover:text-white hover:bg-neutral-700 transition">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-6 overflow-y-auto flex flex-col gap-4">
              {countries[selectedCountry].articles.map((art, i) => (
                <div key={i} className="p-4 rounded-xl bg-neutral-800/40 border border-neutral-800/80 hover:bg-neutral-800/60 transition group relative">
                  <a href={art.url} target="_blank" rel="noopener noreferrer" className="absolute inset-0 z-10" aria-label="Read article" />
                  <h4 className="text-lg font-semibold text-white leading-tight mb-2 group-hover:text-blue-400 transition-colors">{art.title}</h4>
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-xs uppercase font-bold text-blue-500 bg-blue-500/10 px-2 py-1 rounded-sm">{art.source}</span>
                    <div className="flex items-center gap-2">
                      {art.sentiment && (
                        <span className={`text-[10px] font-bold px-2 py-1 rounded-full border ${getSentimentBadgeStyle(art.sentiment.sentiment)}`}>
                          {art.sentiment.label}
                        </span>
                      )}
                      {art.publish_date && <span className="text-xs text-neutral-500">{new Date(art.publish_date).toLocaleDateString()}</span>}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
