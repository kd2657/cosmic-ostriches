# 🛠️ Session Modification History (News Narrative Explorer)

This document serves as a comprehensive, strictly chronological log of every change, addition, and refactor implemented during the current development session. It includes core technical strategies and specific code diffs/snippets for reference.

---

### 1. Windows Environment Dependency Fix
**Goal:** Fix failing environment setup on Windows machines due to async libraries.
- **File Modified:** `backend/requirements.txt`
- **Method:** Added platform-conditional environment markers so `uvloop` is strictly ignored on Windows, resolving fatal `pip install` loop errors.
- **Code Details:**
```text
# Changed from:
httptools==0.6.1
uvloop==0.19.0

# Changed to:
httptools==0.6.1; sys_platform != 'win32'
uvloop==0.19.0; sys_platform != 'win32'
```

### 2. Dark Mode Dropdown UI Fix
**Goal:** Resolve invisible dropdown options in Chromium/Webkit engines rendering white-on-white.
- **File Modified:** `frontend/src/app/cluster/page.tsx`
- **Method:** Hardcoded Tailwind classes directly onto every `<option>` tag to permanently enforce black backgrounds.
- **Code Details:**
```tsx
// Changed from:
<option value="umap">UMAP</option>

// Changed to:
<option className="bg-neutral-900 text-white" value="umap">UMAP</option>
```

### 3. "Deep-Dive" Article Reading Page
**Goal:** Enable seamless "overview-to-detail" drill-down reading with state preservation.
- **Files Modified:** `backend/ml.py`, `backend/main.py`, `frontend/src/app/cluster/page.tsx`, `frontend/src/app/article/[id]/page.tsx`
- **Backend Details:**
Implemented a direct ID lookup to ChromaDB to extract uncompressed text.
```python
# backend/ml.py
def get_article_by_id(article_id: str) -> Optional[Dict[str, Any]]:
    data = collection.get(ids=[article_id], include=["metadatas", "documents"])
    ...
```
```python
# backend/main.py
@app.get("/api/article/{article_id:path}")
def fetch_single_article(article_id: str):
    ...
```
- **Frontend Details:**
Hijacked Plotly's internal scatter interactions to inject URL search parameters (`q`, `algo`, `dim`, `k`).
```tsx
// frontend/src/app/cluster/page.tsx
onClick={(e: any) => {
    if (e.points && e.points.length > 0) {
        const articleId = e.points[0].customdata;
        const urlParams = new URLSearchParams({ q: query, algo: algorithm, dim: dimReduction });
        router.push(`/article/${encodeURIComponent(articleId)}?${urlParams.toString()}`);
    }
}}
```

### 4. Algorithm Selection UX / Nomenclature Refactor
**Goal:** Make the ML configuration dashboard intuitive for non-technical audiences.
- **File Modified:** `frontend/src/app/cluster/page.tsx`
- **Method & Code Details:**
Added `Info` icons and transformed `<select>` nomenclature. Used lightweight HTML `title` attributes for tooltips instead of bloated JS modals.
```tsx
// Added clear labelings with inline Lucide React Info icons
<span className="text-sm text-neutral-400 hidden lg:inline-flex items-center gap-1 cursor-help" title="Controls how high-dimensional data is projected into 2D.">
  Projection Method <Info className="w-3 h-3" />
</span>

// User-friendly selections
<option className="bg-neutral-900 text-white" value="hdbscan" title="Automatically finds groups without choosing a number.">
  HDBSCAN (Automatic)
</option>
<option className="bg-neutral-900 text-white" value="kmeans" title="Lets you control the number of narrative groups.">
  K-Means (Set group count)
</option>
```

### 5. Narrative Diversity Score (NDS) - Cluster Level Metric
**Goal:** Calculate mapping of internal cohesion logic per-narrative (0 - 1.0).
- **Files Modified:** `models/metrics.py`, `backend/ml.py`, `frontend/src/app/cluster/page.tsx`
- **Backend Details:**
Created a pure isolated numpy helper computing Inverse Average Cosine Similarity.
```python
# models/metrics.py
sim_matrix = util.cos_sim(cluster_embs, cluster_embs).numpy()
np.fill_diagonal(sim_matrix, 0)
sum_sim = np.sum(sim_matrix)
avg_sim = sum_sim / (n * (n - 1))
nds = 1.0 - float(avg_sim)
```
- **UI Details:**
Added rendering inside the "AI Summaries" UI box with conditional coloring block.
```tsx
// frontend/src/app/cluster/page.tsx
<div className="text-xs text-neutral-400 pl-1">
  Diversity: {ndsScores[clusterId.toString()].toFixed(2)} (
  <span className={ndsScores[clusterId.toString()] >= 0.60 ? "text-orange-400" : ndsScores[clusterId.toString()] < 0.30 ? "text-green-400" : "text-yellow-400"}>
    {ndsScores[clusterId.toString()] < 0.30 ? "Low/cohesive" : ndsScores[clusterId.toString()] >= 0.60 ? "High/diverse" : "Moderate"}
  </span>)
</div>
```

### 6. Distance from Narrative Center - Article Level Metric
**Goal:** Pinpoint individual relevancy scores (peripheral vs core) in tooltips.
- **Files Modified:** `models/metrics.py`, `backend/ml.py`, `frontend/src/app/cluster/page.tsx`
- **Backend Details:**
Built a centroid matrix vector operation isolated mathematically from existing structures.
```python
# models/metrics.py
centroid = np.mean(cluster_embs, axis=0) # Extract central narrative theme
centroid_tensor = np.expand_dims(centroid, axis=0)
sims = util.cos_sim(cluster_embs, centroid_tensor).numpy().flatten()
dists = np.maximum(0.0, 1.0 - sims)
```
- **UI Details:**
Injected HTML payload cleanly into Plotly's static data tracer.
```tsx
// frontend/src/app/cluster/page.tsx (Inside text mapping array)
let distHtml = "";
if (d.distance_from_center !== undefined && clusterId !== -1) {
    let label = "Typical";
    if (d.distance_from_center < 0.15) label = "Core";
    else if (d.distance_from_center >= 0.30) label = "Peripheral";
    distHtml = `<br><br><span style="color:#fbbf24;">Distance from Narrative Center: ${d.distance_from_center.toFixed(2)} (${label})</span>`;
}

// Appended to final template
return `<b>${d.source}</b><br>${d.title} ... ${distHtml}`;
```

---
*Generated by Antigravity AI Assistant.*
