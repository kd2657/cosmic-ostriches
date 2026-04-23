import { useState } from "react";
import { Activity, X, Info } from "lucide-react";

export default function MetricsOverlay({ metrics, title = "Algorithm Metrics" }: { metrics: any, title?: string }) {
  const [isOpen, setIsOpen] = useState(false);
  const [isHovered, setIsHovered] = useState(false);

  if (!metrics || Object.keys(metrics).length === 0) return null;

  return (
    <>
      <div 
        className="fixed right-0 top-1/2 -translate-y-1/2 z-50 flex items-center group cursor-pointer"
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
        onClick={() => setIsOpen(true)}
      >
        <div className={`overflow-hidden transition-all duration-300 ease-in-out bg-blue-600/80 hover:bg-blue-500 backdrop-blur-md text-white shadow-lg rounded-l-full py-3 flex items-center ${isHovered ? 'w-50 px-5' : 'w-12 pl-3'}`}>
          <Activity className="w-5 h-5 shrink-0" />
          <div className={`flex flex-col ml-3 transition-opacity duration-300 ${isHovered ? 'opacity-100' : 'opacity-0'}`}>
            <span className="whitespace-nowrap font-bold text-sm">Evaluation Metrics</span>
          </div>
        </div>
      </div>

      {isOpen && (
        <div 
          className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200"
          onClick={() => setIsOpen(false)}
        >
          <div 
            className="bg-neutral-900 border border-neutral-800 rounded-2xl shadow-2xl w-full max-w-sm overflow-hidden text-neutral-200" 
            onClick={e => e.stopPropagation()}
          >
            <div className="flex justify-between items-center p-4 border-b border-neutral-800 bg-neutral-950/50">
              <div className="flex items-center gap-2">
                <Activity className="w-5 h-5 text-blue-500" />
                <h3 className="font-bold">{title}</h3>
              </div>
              <button onClick={() => setIsOpen(false)} className="text-neutral-500 hover:text-white transition-colors">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-4 space-y-4 max-h-[70vh] overflow-y-auto custom-scrollbar">
              {Object.entries(metrics).map(([key, value]) => (
                <div key={key} className="flex flex-col bg-neutral-800/40 p-3 rounded-lg border border-neutral-700/50">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs font-bold uppercase tracking-wider text-neutral-400">
                      {key.replace(/_/g, ' ')}
                    </span>
                  </div>
                  <span className="text-lg font-mono text-blue-300">{String(value)}</span>
                </div>
              ))}
              <div className="flex items-start gap-2 mt-4 text-xs text-neutral-400 bg-blue-900/10 p-3 rounded border border-blue-900/30">
                <Info className="w-4 h-4 shrink-0 mt-0.5 text-blue-500" />
                <div className="space-y-1">
                  <p>Interpret scores: <b>Higher</b> Silhouette/NDS indicates better narrative separation and diversity.</p>
                  <p><b>Lower</b> Davies-Bouldin indicates more compact, well-defined clusters.</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
