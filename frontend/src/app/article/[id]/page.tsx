"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams, useParams } from "next/navigation";
import { ArrowLeft, ExternalLink, Loader2 } from "lucide-react";

const sentimentBadgeStyles: Record<string, string> = {
  positive: "bg-emerald-950/70 text-emerald-300 border-emerald-800",
  slightly_positive: "bg-lime-950/70 text-lime-300 border-lime-800",
  slightly_negative: "bg-rose-950/70 text-rose-300 border-rose-800",
  negative: "bg-red-950/70 text-red-300 border-red-800",
};

const getSentimentBadgeStyle = (sentiment: string) =>
  sentimentBadgeStyles[sentiment] ?? "bg-neutral-900/70 text-neutral-300 border-neutral-700";

type ArticleSentiment = {
  label: string;
  sentiment: string;
  confidence: number;
  polarity?: number;
  scores: Record<string, number>;
};

type Article = {
  id: string;
  title?: string;
  description?: string;
  url?: string;
  source?: string;
  body?: string;
  publish_date?: string;
  sentiment?: ArticleSentiment | null;
};

const formatTextIntoParagraphs = (text: string) => {
  if (!text) return ["Content unavailable."];
  
  if (text.includes('\\n')) {
    return text.split('\\n').filter(p => p.trim());
  }
  
  const sentences = text.match(/[^.!?]+[.!?]+/g) || [text];
  const paragraphs = [];
  let currentParagraph = "";
  
  for (let i = 0; i < sentences.length; i++) {
    currentParagraph += sentences[i] + " ";
    if ((i + 1) % 4 === 0 || i === sentences.length - 1) {
      paragraphs.push(currentParagraph.trim());
      currentParagraph = "";
    }
  }
  
  return paragraphs;
};

export default function ArticlePage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const params = useParams();
  
  const [article, setArticle] = useState<Article | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const fetchArticle = async () => {
      try {
        const id = params.id as string;
        const decodedId = decodeURIComponent(id);
        const res = await fetch(`http://localhost:8000/api/article/${encodeURIComponent(decodedId)}`);
        if (!res.ok) throw new Error("Failed to load article");
        const json = await res.json();
        if (json.status === "success" && json.article) {
          setArticle(json.article);
        } else {
          throw new Error("Article not found in database");
        }
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Failed to load article");
      } finally {
        setLoading(false);
      }
    };
    if (params.id) fetchArticle();
  }, [params.id]);

  const handleBack = () => {
    const urlParams = new URLSearchParams(searchParams.toString());
    const from = searchParams.get("from");

    if (from === "search") {
      router.back();
      return;
    }

    router.push(`/cluster?${urlParams.toString()}`);
  };

  return (
    <div className="min-h-screen bg-black text-white selection:bg-blue-500/30 font-sans p-8">
      <div className="max-w-3xl mx-auto mt-12 bg-neutral-900 border border-neutral-800 rounded-2xl overflow-hidden shadow-2xl p-8">
        
        <button 
          onClick={handleBack}
          className="flex items-center gap-2 text-neutral-400 hover:text-white transition-colors mb-8 group cursor-pointer"
        >
          <ArrowLeft className="w-5 h-5 group-hover:-translate-x-1 transition-transform" />
          Back to Visualization
        </button>

        {loading && (
          <div className="flex flex-col items-center justify-center py-20">
            <Loader2 className="w-10 h-10 animate-spin text-blue-500 mb-4" />
            <p className="text-neutral-500 animate-pulse">Retrieving article...</p>
          </div>
        )}

        {error && !loading && (
          <div className="bg-red-950/50 border border-red-900 text-red-200 p-6 rounded-xl text-center py-12">
            <p className="font-medium text-lg mb-2">Error Loading Narrative</p>
            <p className="text-red-400/80">{error}</p>
          </div>
        )}

        {article && !loading && (
          <div className="animate-in fade-in slide-in-from-bottom-4 duration-700">
            <div className="flex items-center gap-3 mb-6">
              <span className="font-bold text-xs tracking-widest uppercase text-blue-400 bg-blue-900/30 px-3 py-1 rounded-full border border-blue-900/50">
                {article.source || "Unknown Source"}
              </span>
              <span className="text-sm font-mono text-neutral-500">
                {article.publish_date ? new Date(article.publish_date).toLocaleDateString() : ""}
              </span>
              {article.sentiment && (
                <span className={`text-xs font-bold px-3 py-1 rounded-full border ${getSentimentBadgeStyle(article.sentiment.sentiment)}`}>
                  {article.sentiment.label}
                </span>
              )}
            </div>
            
            <h1 className="text-3xl md:text-4xl font-bold leading-tight mb-8 text-neutral-100">
              {article.title}
            </h1>

            <div className="prose prose-invert prose-lg max-w-none mb-10 text-neutral-300">
              {formatTextIntoParagraphs(article.body || article.description || "Content unavailable.")
                .map((paragraph: string, i: number) => (
                  paragraph.trim() ? <p key={i} className="leading-relaxed mb-6">{paragraph}</p> : null
              ))}
            </div>

            {article.url && (
              <div className="pt-8 border-t border-neutral-800">
                <a 
                  href={article.url} 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-500 text-white px-6 py-3 rounded-xl font-medium transition-colors"
                >
                  Read Original on Source Website
                  <ExternalLink className="w-4 h-4" />
                </a>
              </div>
            )}
          </div>
        )}

      </div>
    </div>
  );
}
