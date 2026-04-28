import Link from "next/link";
import { ArrowLeft } from "lucide-react";

export default function AboutPage() {
  return (
    <div className="min-h-screen bg-neutral-950 text-neutral-300 flex flex-col items-center py-24 px-6 font-sans">
      <div className="w-full max-w-2xl space-y-16">
        
        {/* Back Link */}
        <div>
          <Link href="/" className="inline-flex items-center gap-2 text-neutral-500 hover:text-white transition-colors text-sm font-mono">
            <ArrowLeft className="w-4 h-4" /> Back to Search
          </Link>
        </div>

        {/* Welcome Section */}
        <section className="space-y-4">
          <h1 className="text-4xl md:text-5xl font-extrabold text-white tracking-tight">The Local Minima</h1>
          <p className="text-sm font-mono text-neutral-500 uppercase tracking-widest">
            A News Narrative Explorer
          </p>
        </section>

        {/* Motivation */}
        <section className="space-y-6">
          <h2 className="text-2xl font-bold text-white tracking-tight border-b border-neutral-800 pb-2">Motivation</h2>
          <div className="space-y-4 text-neutral-400 leading-relaxed text-base">
            <p>
              <strong className="text-neutral-200">Break through the noise.</strong> Modern media is a deluge of sensationalized and biased information. The Local Minima is designed to help you navigate through this flood and find real news narratives.
            </p>
            <p>
              <strong className="text-neutral-200">Take control of news narratives you see.</strong> Instead of centralized sources dictating what you should read, control what you see yourself through data-driven exploration.
            </p>
            <p>
              <strong className="text-neutral-200">No Ads. No Trackers. No Memory.</strong> Your exploration should be yours. The Local Minima doesn't build user profiles, inject advertisements, and forgets you the moment you close the tab.
            </p>
          </div>
        </section>

        {/* Features */}
        <section className="space-y-6">
          <h2 className="text-2xl font-bold text-white tracking-tight border-b border-neutral-800 pb-2">The Core</h2>
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-semibold text-neutral-200">1. News Clusters</h3>
              <p className="text-neutral-400 mt-1 leading-relaxed">Aggregates and semantically groups similar articles, allowing you to quickly digest multiple perspectives on a single event.</p>
            </div>
            <div>
              <h3 className="text-lg font-semibold text-neutral-200">2. Daily Gradient</h3>
              <p className="text-neutral-400 mt-1 leading-relaxed">A real-time snapshot of the shifting themes across the global news landscape, giving you a top-down view of today's dominant topics.</p>
            </div>
            <div>
              <h3 className="text-lg font-semibold text-neutral-200">3. Global Maxima</h3>
              <p className="text-neutral-400 mt-1 leading-relaxed">Visualizes the most prominent narratives occurring worldwide, mapping out high-impact stories based on global coverage density.</p>
            </div>
            <div>
              <h3 className="text-lg font-semibold text-neutral-200">4. Latent Bias</h3>
              <p className="text-neutral-400 mt-1 leading-relaxed">Examines how different publications and outlets report on the exact same topic, exposing underlying editorial biases and variations in narratives.</p>
            </div>
            <div>
              <h3 className="text-lg font-semibold text-neutral-200">5. Recommendations</h3>
              <p className="text-neutral-400 mt-1 leading-relaxed">An embedding-based ranking system that suggests related narratives without relying on manipulative engagement algorithms, keeping the focus strictly on relevance.</p>
            </div>
          </div>
        </section>

        {/* Algorithms */}
        <section className="space-y-6">
          <h2 className="text-2xl font-bold text-white tracking-tight border-b border-neutral-800 pb-2">The Engine</h2>
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-semibold text-neutral-200">1. Semantic Vector Embeddings</h3>
              <p className="text-neutral-400 mt-1 leading-relaxed"><strong className="text-neutral-300">all-MiniLM-L6-v2 & Cosine Similarity:</strong> We use language models to transform news articles into dense, high-dimensional vectors. While the model handles the complex tokenization and contextualization, the core mechanism we rely on to quickly compare these articles is cosine similarity. This metric allows us to accurately determine how close two articles are in semantic meaning, regardless of their exact wording.</p>
            </div>
            <div>
              <h3 className="text-lg font-semibold text-neutral-200">2. Projection</h3>
              <p className="text-neutral-400 mt-1 leading-relaxed"><strong className="text-neutral-300">UMAP (Uniform Manifold Approximation and Projection):</strong> Because semantic embeddings exist in hundreds of dimensions, we use projection algorithms to compress them down to a visualizable 2D or 3D space. While custom PCA and t-SNE are also implemented, UMAP is our primary choice because it strikes an ideal balance between preserving local neighborhoods and maintaining global structures, letting users intuitively &quot;see&quot; the accurate news landscape.</p>
            </div>
            <div>
              <h3 className="text-lg font-semibold text-neutral-200">3. Clustering</h3>
              <p className="text-neutral-400 mt-1 leading-relaxed"><strong className="text-neutral-300">HDBSCAN (Hierarchical Density-Based Spatial Clustering):</strong> Once articles are embedded and projected, we use clustering algorithms to locate the densest regions of data points. While custom K-Means is available, HDBSCAN was chosen as the primary engine because it does not require us to pre-guess the number of clusters and it gracefully filters out noise, accurately grouping complex, non-spherical shapes into bounded news narratives.</p>
            </div>
            <div>
              <h3 className="text-lg font-semibold text-neutral-200">4. Furthest Point Algorithm</h3>
              <p className="text-neutral-400 mt-1 leading-relaxed"><strong className="text-neutral-300">Furthest Point Sampling (K-Center Greedy):</strong> To ensure our summaries and recommendations aren&apos;t just echoing the exact same perspective repeatedly, we employ the Furthest Point Algorithm. By iteratively selecting the article that is furthest away from our already-chosen set in the vector space, we guarantee a highly diverse and representative sample that covers the maximum surface area of a topic without redundancy.</p>
            </div>
            <div>
              <h3 className="text-lg font-semibold text-neutral-200">5. Various Evaluation Metrics</h3>
              <p className="text-neutral-400 mt-1 leading-relaxed"><strong className="text-neutral-300">Cluster Quality Validation:</strong> We continuously validate the quality and tightness of our grouped narratives using rigorous statistical measures. Metrics like the Silhouette Score or custom cluster variance calculations allow the system to quantitatively grade how well-defined our news clusters are, ensuring that the narratives we present are mathematically robust and distinct.</p>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
