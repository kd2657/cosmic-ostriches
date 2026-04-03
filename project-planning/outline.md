# **Project Structuring**

## ***Project Name:** The Local Minima*

## ***Step 0 (Basic Interface)***

- ### *Home/Article Search Page*
  - Allows user to search for articles that match a particular search query
- ### *Clustering Page*
  - Implementation of core site feature
- ### *Login/Account Page (Under Consideration)*
  - *Allows user to create, login, and delete their account*

## ***Step 1 (Basic/Core Feature)***

- ### *News Narrative Explorer*
  - Compare how different news sources cover the same events and discover: Similar reporting clusters, Narrative differences, Topic framing differences, Bias or emphasis patterns  
  - User selects news sources → app visualizes similarity structure.
    - Must-use Dimensionality Reduction: PCA (explore UMAP, t-SNE)
    - Must-use Clustering: k-means, Gaussian mixture (explore DBSCAN)
    - Must-use Similarity Analysis: cosine similarity (explore others)
  - Most likely separate tab for this

## ***Step 2 (Addtitional Features): \(Design-in-Progress\)***
  - ### *Narrative Diversity Score*  
    - Each cluster is treated as one “event”
    - *Diversity \= mean squared distance to cluster centroid (connected closely to what we have learned in class)*
    - Keyword distribution differences (for visualization)
    - Enables users to "quantify" how controversial or contested an event is across different media sources
  
  - ### *Cross-Source Contradiction Finder*
    - Identifies the pair of articles (from different sources) that report on the same event but have the most different narratives, sentiment, or framing
    - Define a simple contradiction score (e.g. Similarity times "Narrative Difference")
    - Hopefully integrate with existing visualization (e.g. clusters)
      
- ### *Source Influence Score*  
  - Event Centroid
    - centroid = mean of all embeddings of all articles in the event
    - represents the **consensus narrative**
  - For each source within the event:
    - compute the average embedding of its articles:
    - *source\_vector = mean of embeddings of articles from that source*
    - *influence = 1 / (distance + ε)*
  - High influence → close to centroid → aligns with dominant / consensus narrative  
  - Low influence → far from centroid → presents alternative or divergent framing

## ***Step 3 (Unconfirmed Features): \(Design-in-Progress\)***

 - ### *Article Enjoyment Labeler*

    - Given a list of articles the user “enjoys”, look for key words/phrases that appear more than articles not on the list. Then use this to predict other articles the user likes/give a likelihood of user enjoying an article

- ### *Blind Newstand*

  - User has option to select their usual news sources, and we then compile articles that they likely aren’t seeing based on their current preferences (either explicitly or implicitly)