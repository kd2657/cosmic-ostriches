# Project Constraints
- The project should maximize stability (not crashing/freezing) over functionality and especially aesthetics
- The project should be essentially free to run (one-off, low payments at most tolerable)
- The project should be able to run locally on a descently powerful laptop
- The project should be able to be deployed on a free tier of a cloud platform (e.g. Vercel, Render, etc.) in later stages
- Technical Constraints:
    - Must give K-Means clustering as a UI friendly option (e.g. allow user to select number of clusters)
    - Must give Mixture of Gaussians as a UI friendly option in the similar way
    - If the user does not wish to specify a k-value, use HDBSCAN as the default clustering algorithm