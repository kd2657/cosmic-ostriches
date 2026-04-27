import { ThumbsUp, ThumbsDown, Link as LinkIcon } from "lucide-react";

type Article = {
  id: string;
  title: string;
  description?: string;
  body?: string;
  source?: string;
  publish_date?: string;
  url?: string;
  match_score: number;
};

interface RecommendedDisplayProps {
  recommended: Article[];
  votes: Record<string, "up" | "down" | null>;
  handleVote: (articleId: string, vote: "up" | "down") => void;
}

export default function RecommendedDisplay({ recommended, votes, handleVote }: RecommendedDisplayProps) {
  return (
    <div className="z-10 w-full max-w-5xl mx-auto mt-12 space-y-4 pb-20 animate-in fade-in duration-500">
      <h2 className="text-2xl font-bold text-white mb-6 border-b border-neutral-800 pb-2 flex justify-between items-end">
        <span>Recommended For You</span>
        <span className="text-sm font-normal text-neutral-500">
          {recommended.length} Results
        </span>
      </h2>

      {recommended.length === 0 ? (
        <p className="text-neutral-500 text-sm">No recommended articles</p>
      ) : (
        <div className="grid gap-4">
          {recommended.map((a, i) => (
            <div
              key={`rec-${i}`}
              className="bg-neutral-900/50 border border-neutral-800 rounded-xl p-5 hover:bg-neutral-800/80 transition-colors backdrop-blur-md"
            >
              <h3 className="text-lg font-semibold text-neutral-100 mb-2">
                {a.title}
              </h3>

              <p className="text-neutral-400 text-sm mb-3 line-clamp-3">
                {(a.body || "").slice(0, 250)}...
              </p>

              <div className="flex justify-between items-center">
                <span className="text-xs text-neutral-500">{a.source}</span>

                <div className="flex items-center gap-2">
                  {a.url && (
                    <a
                      href={a.url}
                      target="_blank"
                      rel="noreferrer"
                      className="flex items-center gap-1 text-blue-400 hover:text-blue-300 bg-blue-900/20 px-3 py-1 rounded-full transition-colors text-xs font-semibold"
                    >
                      <LinkIcon className="w-3 h-3" /> Read Article
                    </a>
                  )}

                  <button
                    onClick={() => handleVote(a.id, "up")}
                    className={`p-2 rounded-lg transition ${
                      votes[a.id] === "up"
                        ? "bg-emerald-600 text-white shadow-lg"
                        : "bg-emerald-900/20 hover:bg-emerald-800/40 text-emerald-400"
                    }`}
                  >
                    <ThumbsUp className="w-4 h-4" />
                  </button>

                  <button
                    onClick={() => handleVote(a.id, "down")}
                    className={`p-2 rounded-lg transition ${
                      votes[a.id] === "down"
                        ? "bg-red-600 text-white shadow-lg"
                        : "bg-red-900/20 hover:bg-red-800/40 text-red-400"
                    }`}
                  >
                    <ThumbsDown className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
