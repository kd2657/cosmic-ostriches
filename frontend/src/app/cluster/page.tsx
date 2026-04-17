"use client";

import { useState, useEffect, Suspense, useRef } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import dynamic from "next/dynamic";
import { ArrowLeft, Loader2, Settings2, Sparkles, Info } from "lucide-react";

// Plotly needs to be loaded dynamically with ssr disabled
const Plot = dynamic(() => import("react-plotly.js"), { 
  ssr: false, 
  loading: () => (
    <div className="flex items-center justify-center h-full w-full bg-neutral-900 rounded-2xl animate-pulse">
      <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
    </div>
  ) 
});

function ClusterContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const query = searchParams.get("q") || "";
  const localParam = searchParams.get("local") === "true";
  
  const [data, setData] = useState<any[]>([]);
  const [summaries, setSummaries] = useState<Record<string, {title: string, summary: string} | string>>({});
  const [ndsScores, setNdsScores] = useState<Record<string, number>>({});
  const [selectedCluster, setSelectedCluster] = useState<number | null>(null);
  const [isLocalSummary, setIsLocalSummary] = useState(false);
  const [isOfflineCache, setIsOfflineCache] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  
  const [algorithm, setAlgorithm] = useState("hdbscan");
  const [kValue, setKValue] = useState<number | "">("");
  const [dimReduction, setDimReduction] = useState("umap");
  const abortControllerRef = useRef<AbortController | null>(null);
  const lastRequestKeyRef = useRef("");

  const fetchData = async (
    algo: string,
    k: number | "",
    dimRed: string,
    options?: { dedupe?: boolean }
  ) => {
    if (!query) return;

    const requestKey = JSON.stringify({ query, algorithm: algo, k, dimReduction: dimRed });
    if (options?.dedupe && lastRequestKeyRef.current === requestKey) return;

    lastRequestKeyRef.current = requestKey;
    abortControllerRef.current?.abort();
    const controller = new AbortController();
    abortControllerRef.current = controller;

    setLoading(true);
    setError("");
    
    try {
      const payload: any = { query, algorithm: algo, dim_reduction: dimRed, force_local: localParam };
      if (k !== "") payload.k = k;
      
      const res = await fetch("http://localhost:8000/api/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
        signal: controller.signal
      });
      
      if (!res.ok) throw new Error("Failed to fetch data from backend");
      
      const json = await res.json();
      if (abortControllerRef.current !== controller) return;

      if (json.status === "success") {
        setData(json.results.points || []);
        setSummaries(json.results.summaries || {});
        setNdsScores(json.results.nds_scores || {});
        setIsLocalSummary(json.results.is_local_summary || false);
        setIsOfflineCache(json.results.is_offline_cache || false);
      } else {
        throw new Error(json.detail || "Unknown error");
      }
    } catch (err: any) {
      if (err.name === "AbortError") return;
      setError(err.message);
    } finally {
      if (abortControllerRef.current === controller) {
        setLoading(false);
      }
    }
  };

  useEffect(() => {
    fetchData(algorithm, kValue, dimReduction);
    return () => abortControllerRef.current?.abort();
  }, [query]);

  useEffect(() => {
    if (isOfflineCache) {
      const timer = setTimeout(() => setIsOfflineCache(false), 4000);
      return () => clearTimeout(timer);
    }
  }, [isOfflineCache]);

  const handleApplySettings = () => {
    fetchData(algorithm, kValue, dimReduction);
  };

  // Group data by cluster for Plotly with Cosmetic Mapping fixes
  const uniqueClusters = Array.from(new Set(data.map(d => d.cluster)));
  
  // Sort clusters ascending (but forcefully move -1 to the end)
  uniqueClusters.sort((a, b) => {
    if (a === -1) return 1;
    if (b === -1) return -1;
    return a - b;
  });

  const VIBRANT_COLORS = [
    "#00f0ff", // Neon Cyan
    "#ff003c", // Cyber Red
    "#bc13fe", // Electric Purple
    "#a1ff0a", // Acid Green
    "#ff7f00", // Laser Orange
    "#ffea00", // Cyber Yellow
    "#ff00a0", // Shocking Pink
    "#5d00ff"  // Neon Indigo
  ];

  const plotData = uniqueClusters.map(clusterId => {
    const clusterPoints = data.filter(d => d.cluster === clusterId);
    const isSelected = selectedCluster === null || selectedCluster === clusterId;
    const baseColor = clusterId === -1 ? "#525252" : VIBRANT_COLORS[Math.abs(clusterId) % VIBRANT_COLORS.length];
    
    return {
      x: clusterPoints.map(d => d.x),
      y: clusterPoints.map(d => d.y),
      customdata: clusterPoints.map(d => d.id),
      type: "scatter",
      mode: "markers",
      name: clusterId === -1 ? "Noise (Unclustered)" : `Narrative ${clusterId + 1}`,
      text: clusterPoints.map(d => {
        let distHtml = "";
        if (d.distance_from_center !== undefined && clusterId !== -1) {
          const dist = d.distance_from_center;
          if (dist < 0.2) distHtml = `<br><br><span style="color:#d9f99d;">🟢 Core article (Dist: ${dist})</span>`;
          else if (dist < 0.4) distHtml = `<br><br><span style="color:#fef08a;">🟡 Typical article (Dist: ${dist})</span>`;
          else distHtml = `<br><br><span style="color:#fca5a5;">🔴 Peripheral article (Dist: ${dist})</span>`;
        }
        return `<b>${d.source}</b><br>${d.title}${distHtml}`;
      }),
      hoverinfo: "text",
      hoverlabel: { bgcolor: "#171717", font: { color: "white" }, align: "left" },
      marker: {
        size: 12,
        opacity: clusterId === -1 ? (isSelected ? 0.25 : 0.05) : (isSelected ? 0.85 : 0.1),
        line: { width: 1, color: "#171717" },
        color: baseColor
      }
    };
  });

  return (
    <div className="min-h-screen bg-neutral-950 text-white p-6 md:p-10 flex flex-col h-screen">
      <header className="flex items-center justify-between mb-8 flex-shrink-0 z-10 w-full">
        <div className="flex items-center gap-4">
          <button onClick={() => router.push(`/?q=${encodeURIComponent(query)}`)} className="p-2 hover:bg-neutral-800 rounded-full transition-colors cursor-pointer">
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <h1 className="text-2xl font-bold">Query: <span className="text-blue-400">"{query}"</span></h1>
            <p className="text-neutral-500 text-sm">Visualizing structural narratives</p>
          </div>
        </div>
        
        <div className="flex items-center gap-4 bg-neutral-900 border border-neutral-800 p-2 rounded-xl">
          <div className="flex items-center gap-2 px-3 border-r border-neutral-800">
            <Settings2 className="w-4 h-4 text-neutral-400" />
            <span className="text-sm text-neutral-400 hidden lg:inline-flex items-center gap-1 cursor-help" title="Controls how high-dimensional data is projected into 2D.">
              Projection Method <Info className="w-3 h-3" />
            </span>
            <select 
              value={dimReduction} 
              onChange={(e) => setDimReduction(e.target.value)}
              className="bg-transparent text-sm focus:outline-none cursor-pointer text-blue-400 font-medium pr-1"
            >
              <option className="bg-neutral-900 text-white" value="umap" title="Good for exploring both local clusters and overall structure.">UMAP (Balanced)</option>
              <option className="bg-neutral-900 text-white" value="tsne" title="Prioritizes distinct, separated local clusters.">t-SNE (Cluster-focused)</option>
              <option className="bg-neutral-900 text-white" value="pca" title="Provides a quick, linear overview of main variances.">PCA (Overview)</option>
            </select>
          </div>
          
          <div className="flex items-center gap-2 px-3 border-r border-neutral-800">
            <span className="text-sm text-neutral-400 hidden lg:inline-flex items-center gap-1 cursor-help" title="Algorithm to group similar articles into distinct narratives.">
              Clustering Method <Info className="w-3 h-3" />
            </span>
            <select 
              value={algorithm} 
              onChange={(e) => setAlgorithm(e.target.value)}
              className="bg-transparent text-sm focus:outline-none cursor-pointer pr-1"
            >
              <option className="bg-neutral-900 text-white" value="hdbscan" title="Automatically finds groups of varying densities without choosing a number.">HDBSCAN (Automatic)</option>
              <option className="bg-neutral-900 text-white" value="kmeans" title="Lets you control the exact number of narrative groups.">K-Means (Set group count)</option>
              <option className="bg-neutral-900 text-white" value="gmm" title="Models groups probabilistically.">GMM</option>
              <option className="bg-neutral-900 text-white" value="agglomerative" title="Builds groups hierarchically from bottom up.">Agglomerative</option>
              <option className="bg-neutral-900 text-white" value="affinity" title="Creates groups by data points sending messages to each other.">Affinity</option>
            </select>
          </div>
          
          {(algorithm === "kmeans" || algorithm === "gmm" || algorithm === "agglomerative") && (
            <div className="flex items-center gap-2 px-2 border-r border-neutral-800">
              <span className="text-sm text-neutral-400">Groups</span>
              <input 
                type="number" 
                min="2" max="20"
                value={kValue}
                onChange={(e) => setKValue(e.target.value ? parseInt(e.target.value) : "")}
                className="w-12 bg-neutral-800 rounded px-1 text-center text-sm focus:outline-none"
                placeholder="Auto"
              />
            </div>
          )}
          
          <button 
            onClick={handleApplySettings}
            disabled={loading}
            className="px-4 py-1.5 bg-blue-600 hover:bg-blue-500 text-sm rounded-lg font-medium transition-colors cursor-pointer disabled:opacity-50"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : "Update View"}
          </button>
        </div>
      </header>

      <main className="flex-grow flex flex-col min-h-0 space-y-4 relative z-0 w-full overflow-hidden shrink-0">
        {isOfflineCache && (
          <div className="absolute top-4 left-1/2 -translate-x-1/2 z-50 animate-in slide-in-from-top-4 fade-in duration-400">
            <div className="bg-yellow-950 border border-yellow-700 text-yellow-500 px-4 py-2 rounded-full shadow-2xl text-sm flex items-center gap-3 whitespace-nowrap font-medium">
              <span className="flex h-2 w-2 rounded-full bg-yellow-500 animate-pulse shrink-0 shadow-[0_0_8px_rgba(234,179,8,1)]"></span>
              NewsAPI Limit Reached. Displaying locally cached vector-matches.
            </div>
          </div>
        )}
        
        <div className="flex-grow bg-neutral-900 border border-neutral-800 rounded-2xl overflow-hidden relative min-h-[55vh]">
          {loading && (
            <div className="absolute inset-0 z-20 bg-neutral-900/80 backdrop-blur-sm flex flex-col items-center justify-center">
              <Loader2 className="w-10 h-10 animate-spin text-blue-500 mb-4" />
              <p className="text-neutral-400 animate-pulse">Vectorizing, clustering, and generating AI summaries...</p>
            </div>
          )}
          
          {error && (
            <div className="absolute inset-0 z-20 flex items-center justify-center p-6">
              <div className="bg-red-950/50 border border-red-900 text-red-200 p-6 rounded-xl max-w-lg text-center">
                <h3 className="text-xl font-bold mb-2">Error Processing Data</h3>
                <p>{error}</p>
                <button 
                  onClick={() => fetchData(algorithm, kValue, dimReduction)}
                  className="mt-6 px-4 py-2 bg-red-900 hover:bg-red-800 rounded-lg transition-colors cursor-pointer"
                >
                  Retry
                </button>
              </div>
            </div>
          )}

          {!loading && !error && data.length === 0 && (
            <div className="absolute inset-0 z-10 flex items-center justify-center">
              <p className="text-neutral-500">No narrative data found for this query.</p>
            </div>
          )}

          <div className="absolute inset-0 w-full h-full z-0">
            <Plot
              data={plotData as any}
              onLegendClick={(e: any) => {
                const cId = uniqueClusters[e.curveNumber];
                setSelectedCluster(prev => prev === cId ? null : cId);
                return false; 
              }}
              onClick={(e: any) => {
                if (e.points && e.points.length > 0) {
                  const articleId = e.points[0].customdata;
                  const urlParams = new URLSearchParams({ q: query, algo: algorithm, dim: dimReduction });
                  if (kValue !== "") urlParams.append("k", kValue.toString());
                  router.push(`/article/${encodeURIComponent(articleId)}?${urlParams.toString()}`);
                }
              }}
              layout={{
                autosize: true,
                paper_bgcolor: 'transparent',
                plot_bgcolor: 'transparent',
                font: { color: '#a3a3a3' },
                margin: { t: 20, r: 20, b: 20, l: 20 },
                xaxis: { 
                  showgrid: true, gridcolor: '#262626', zerolinecolor: '#404040',
                  showticklabels: false
                },
                yaxis: { 
                  showgrid: true, gridcolor: '#262626', zerolinecolor: '#404040',
                  showticklabels: false
                },
                hovermode: 'closest',
                showlegend: true,
                legend: { orientation: 'h', y: -0.1, font: { size: 16 } }
              }}
              useResizeHandler={true}
              style={{ width: "100%", height: "100%" }}
              config={{ displayModeBar: false, scrollZoom: true }}
            />
          </div>
        </div>

        {/* AI Summarization Panel */}
        {!loading && Object.keys(summaries).length > 0 && (
          <div className="bg-neutral-900 border border-neutral-800 rounded-2xl p-6 overflow-y-auto max-h-[45vh] flex-shrink-0 animate-in fade-in slide-in-from-bottom-2 duration-500">
             <h3 className="text-lg font-bold text-white mb-4 border-b border-neutral-800 pb-2 flex items-center justify-between">
               <div className="flex items-center gap-2">
                 <Sparkles className="w-5 h-5 text-blue-400" />
                 AI Narrative Summaries
               </div>
               {isLocalSummary && (
                 <span className="text-xs font-bold bg-orange-950 text-orange-400 px-2 py-0.5 rounded border border-orange-800">
                   Local Summary Only
                 </span>
               )}
             </h3>
             <div className="space-y-6">
               {uniqueClusters.filter(c => c !== -1).map(clusterId => {
                 if (selectedCluster !== null && selectedCluster !== clusterId) return null;

                 const summaryData = summaries[clusterId.toString()];
                 const isObj = typeof summaryData === 'object' && summaryData !== null;
                 
                 let title = isObj ? (summaryData as any).title : `Narrative ${clusterId + 1}`;
                 let text = isObj ? (summaryData as any).summary : (summaryData || "");

                 if (typeof text === 'string') {
                   if (text.includes('.')) {
                     text = text.substring(0, text.lastIndexOf('.') + 1);
                   } else if (text && text !== "Narrative summary unavailable.") {
                     text = text + '.';
                   }
                 }
                 
                 const clusterPoints = data.filter(d => d.cluster === clusterId);
                 const sources = Array.from(new Set(clusterPoints.map(d => d.source))).filter(Boolean);
                 const baseColor = VIBRANT_COLORS[Math.abs(clusterId) % VIBRANT_COLORS.length];
                 
                 return (
                   <div key={clusterId} className="flex flex-col gap-2">
                      <div className="flex items-center gap-3">
                        <button 
                          onClick={() => setSelectedCluster(prev => prev === clusterId ? null : clusterId)}
                          className="font-bold px-3 py-1 rounded inline-block transition-transform hover:scale-[1.02] cursor-pointer text-left focus:outline-none"
                          style={{ 
                            backgroundColor: baseColor + '33', 
                            color: baseColor, 
                            border: `1px solid ${baseColor}80` 
                          }}
                        >
                          {isObj ? `Narrative ${clusterId + 1}: ${title}` : title}
                        </button>
                        {ndsScores[clusterId.toString()] !== undefined && (
                          <span className={`text-xs px-2 py-0.5 rounded-full font-bold border ${
                            ndsScores[clusterId.toString()] < 0.3 
                              ? 'bg-green-950/50 text-green-400 border-green-900/50' 
                              : ndsScores[clusterId.toString()] < 0.6
                                ? 'bg-yellow-950/50 text-yellow-500 border-yellow-900/50'
                                : 'bg-red-950/50 text-red-400 border-red-900/50'
                          }`} title={`Narrative Diversity Score: ${ndsScores[clusterId.toString()]} (higher means broader discourse)`}>
                            NDS: {ndsScores[clusterId.toString()]}
                          </span>
                        )}
                      </div>
                      <p className="text-neutral-300 leading-relaxed font-medium pl-1">
                        {text}
                      </p>
                      <p className="text-xs text-neutral-500 font-mono uppercase tracking-wider pl-1 mt-1">
                        Sources: <span className="text-neutral-400">{sources.join(", ") || "Unknown"}</span>
                      </p>
                   </div>
                 );
               })}
               
               {uniqueClusters.includes(-1) && (selectedCluster === null || selectedCluster === -1) && (
                 <div className="flex flex-col gap-2 opacity-50 mt-6 pt-6 border-t border-neutral-800/50">
                    <div className="flex items-center gap-3">
                      <button 
                        onClick={() => setSelectedCluster(prev => prev === -1 ? null : -1)}
                        className="font-bold text-neutral-500 bg-neutral-800/50 px-3 py-1 rounded border border-neutral-700/50 cursor-pointer hover:bg-neutral-800 transition-colors"
                      >
                        Narrative Noise
                      </button>
                    </div>
                    <p className="text-neutral-400 italic pl-1">
                      {typeof summaries["-1"] === 'object' && summaries["-1"] !== null ? (summaries["-1"] as any).summary : (summaries["-1"] as string || "Unclustered outliers and noise.")}
                    </p>
                 </div>
               )}
             </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default function ClusterPage() {
  return (
    <Suspense fallback={
      <div className="h-screen flex items-center justify-center bg-neutral-950">
        <Loader2 className="w-8 h-8 animate-spin text-neutral-500" />
      </div>
    }>
      <ClusterContent />
    </Suspense>
  );
}
