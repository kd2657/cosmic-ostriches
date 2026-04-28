"use client";

import { ExternalLink, Loader2, X } from "lucide-react";

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
  description?: string;
  body?: string;
  source?: string;
  publish_date?: string;
  url?: string;
  match_score: number;
  sentiment?: ArticleSentiment | null;
};

type ArticleModalProps = {
  isOpen: boolean;
  loading: boolean;
  error: string;
  article: Article | null;
  onClose: () => void;
};

const sentimentBadgeStyles: Record<string, string> = {
  positive: "bg-emerald-950/70 text-emerald-300 border-emerald-800",
  slightly_positive: "bg-lime-950/70 text-lime-300 border-lime-800",
  slightly_negative: "bg-rose-950/70 text-rose-300 border-rose-800",
  negative: "bg-red-950/70 text-red-300 border-red-800",
};

const getSentimentBadgeStyle = (sentiment: string) =>
  sentimentBadgeStyles[sentiment] ?? "bg-neutral-900/70 text-neutral-300 border-neutral-700";

const formatTextIntoParagraphs = (text: string) => {
  if (!text) return ["Content unavailable."];
  if (text.includes("\\n")) {
    return text.split("\\n").filter((p) => p.trim());
  }
  const sentences = text.match(/[^.!?]+[.!?]+/g) || [text];
  const paragraphs: string[] = [];
  let currentParagraph = "";
  for (let i = 0; i < sentences.length; i++) {
    currentParagraph += `${sentences[i]} `;
    if ((i + 1) % 4 === 0 || i === sentences.length - 1) {
      paragraphs.push(currentParagraph.trim());
      currentParagraph = "";
    }
  }
  return paragraphs;
};

/**
 * ArticleModal: Full-text reader overlay for a single article.
 *
 * Receives open/close state from the parent and renders a slide-up panel
 * with loading, error, and article body states. Clicking the backdrop closes
 * the modal; clicking inside the panel does not.
 */
export default function ArticleModal({ isOpen, loading, error, article, onClose }: ArticleModalProps) {
  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-[80] flex items-center justify-center px-4 py-6 sm:px-6"
      onClick={onClose}
    >
      <div className="absolute inset-0 bg-neutral-950/35 backdrop-blur-[3px]" />
      <div
        className="relative z-10 flex h-[86vh] w-full max-w-4xl flex-col overflow-hidden rounded-[28px] border border-white/10 bg-neutral-950/88 shadow-[0_24px_120px_rgba(0,0,0,0.45)]"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex shrink-0 items-center justify-between gap-4 border-b border-white/10 bg-gradient-to-r from-neutral-950 via-neutral-900 to-neutral-950 px-5 py-4 sm:px-7">
          <div>
            <p className="text-[11px] uppercase tracking-[0.28em] text-cyan-300/70">Article Reader</p>
            <h2 className="mt-1 text-lg font-semibold text-white sm:text-xl">
              {article?.title || "Loading article"}
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-white/10 bg-white/5 text-neutral-300 transition-colors hover:bg-white/10 hover:text-white cursor-pointer"
            aria-label="Close article reader"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Body */}
        <div className="min-h-0 flex-1 overflow-hidden">
          {loading && (
            <div className="flex h-full min-h-72 flex-col items-center justify-center px-5 py-5 text-center sm:px-7 sm:py-6">
              <Loader2 className="mb-4 h-10 w-10 animate-spin text-cyan-400" />
              <p className="text-sm text-neutral-400">Retrieving full article text...</p>
            </div>
          )}

          {error && !loading && (
            <div className="px-5 py-5 sm:px-7 sm:py-6">
              <div className="rounded-2xl border border-red-900/70 bg-red-950/40 p-6 text-center">
                <p className="text-lg font-medium text-red-100">Error loading article</p>
                <p className="mt-2 text-sm text-red-300/80">{error}</p>
              </div>
            </div>
          )}

          {article && !loading && !error && (
            <div className="flex h-full min-h-0 flex-col animate-in fade-in slide-in-from-bottom-2 duration-300">
              {/* Meta row */}
              <div className="shrink-0 px-5 pb-4 pt-5 sm:px-7 sm:pb-5 sm:pt-6">
                <div className="mb-6 flex flex-wrap items-center gap-3">
                  <span className="rounded-full border border-cyan-900/50 bg-cyan-900/25 px-3 py-1 text-xs font-bold uppercase tracking-widest text-cyan-300">
                    {article.source || "Unknown Source"}
                  </span>
                  {article.publish_date && (
                    <span className="text-sm text-neutral-500">
                      {new Date(article.publish_date).toLocaleDateString()}
                    </span>
                  )}
                  {article.sentiment && (
                    <span className={`rounded-full border px-3 py-1 text-xs font-bold ${getSentimentBadgeStyle(article.sentiment.sentiment)}`}>
                      {article.sentiment.label}
                    </span>
                  )}
                </div>
              </div>

              {/* Scrollable body */}
              <div className="min-h-0 flex-1 px-5 pb-4 sm:px-7">
                <div className="h-full overflow-y-auto overscroll-contain rounded-[24px] border border-white/8 bg-white/[0.03] p-5 [scrollbar-gutter:stable] sm:p-7">
                  <div className="space-y-5 text-[15px] leading-8">
                    {formatTextIntoParagraphs(article.body || article.description || "Content unavailable.").map(
                      (paragraph, index) =>
                        paragraph.trim() ? (
                          <p key={index} className="text-neutral-300">
                            {paragraph}
                          </p>
                        ) : null
                    )}
                  </div>
                </div>
              </div>

              {/* Footer link */}
              {article.url && (
                <div className="shrink-0 border-t border-white/8 bg-neutral-950/95 px-5 py-4 sm:px-7">
                  <div className="flex justify-end">
                    <a
                      href={article.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-2 rounded-full border border-blue-500/30 bg-blue-500/15 px-4 py-2 text-sm font-medium text-blue-200 transition-colors hover:bg-blue-500/25 hover:text-white"
                    >
                      Read Article
                      <ExternalLink className="h-4 w-4" />
                    </a>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
