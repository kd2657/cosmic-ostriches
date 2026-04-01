# Visualizations

Here, append and track research and ideas for visualizations across the project.

## ***Clustering Visualizations***

The 2D scatter plot (UMAP/t-SNE/PCA) remains the primary visualization. Below are supplementary visuals to render **underneath** the scatter plot, making the clustering results more informative to users who may not intuitively understand a reduced-dimensionality graph.

All of these can be built with **Plotly.js** (already installed via `react-plotly.js`).

---

### 1. **Cluster Size Distribution — Horizontal Bar Chart**
- A horizontal bar chart where each bar = one cluster, length = number of articles in that cluster.
- Color-coded to match the scatter plot legend colors for visual continuity.
- **Why:** Immediately communicates "which narratives dominate the news cycle" without requiring the user to count dots on a scatter plot. Gives a quantitative anchor to the qualitative scatter layout.
- **Plotly type:** `type: 'bar'`, `orientation: 'h'`

### 2. **Cluster Composition Breakdown — Treemap**
- A nested rectangle layout: outer boxes = clusters, inner boxes = individual media sources within each cluster (sized by article count from that source).
- **Why:** Answers the question "which publishers are driving each narrative?" in a single glance. More intuitive than reading the `Sources:` text list under each AI summary.
- **Plotly type:** `type: 'treemap'` with `labels`, `parents`, `values`

### 3. **Keyword Frequency Tags — Horizontal Bar per Cluster**
- For each cluster, a small horizontal bar chart showing the top 5-8 most frequent/distinctive keywords (via TF-IDF or term frequency).
- **Why:** Gives users an at-a-glance "topic label" for each cluster. Even without reading the AI summary, a user can scan keywords like `"tariff"`, `"trade"`, `"deficit"` and immediately understand the narrative.
- These can be rendered as small inline bar charts within each narrative summary card, or as a separate section.

### 4. **Source Diversity — Pie / Donut Chart**
- A pie or donut chart showing the distribution of unique media publishers across all clusters.
- **Why:** Communicates media diversity and potential bias at the corpus level — "are my results dominated by one outlet?"
- **Plotly type:** `type: 'pie'` with `hole: 0.4` for donut variant

### 5. **Cluster Similarity Heatmap**
- A square heatmap where each axis = cluster ID, cell color = average cosine similarity between the centroids of two clusters.
- **Why:** Reveals which narratives are "close cousins" and which are truly distinct. Users can see that "Narrative 1 and 3 are very similar but Narrative 2 is completely different." This provides context the scatter plot shows spatially but doesn't quantify.
- **Plotly type:** `type: 'heatmap'` with `z` matrix, `x`/`y` as cluster labels

### 6. **Article Count per Source per Cluster — Stacked Bar Chart**
- A stacked bar chart where each bar = one cluster, segments = media sources (color-coded), height = article count.
- **Why:** A more detailed alternative to the treemap — shows both cluster size AND source composition in a compact, familiar format.
- **Plotly type:** `type: 'bar'` with multiple traces, `barmode: 'stack'`

---

### Prioritization Recommendation
For a first implementation pass, the following three give the highest information density for the lowest implementation cost:
1. **Horizontal Bar Chart** (cluster sizes) — trivial to build, immediately useful
2. **Keyword Tags** (per-cluster TF-IDF keywords) — requires backend work but highly informative
3. **Treemap** (source-per-cluster breakdown) — visually impressive and leverages data already in the response payload
