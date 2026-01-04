"""
Function Utilities

Core functions for document clustering: embeddings, clustering, and description generation.
"""

import logging
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from sklearn.cluster import AgglomerativeClustering, DBSCAN, KMeans, SpectralClustering
from sklearn.metrics import calinski_harabasz_score, davies_bouldin_score, silhouette_score

logger = logging.getLogger(__name__)


def generate_embeddings(
    texts: List[str],
    model_name: str = 'bert-base-uncased',
    batch_size: int = 8
) -> np.ndarray:
    """
    Generate embeddings for a list of texts using sentence transformers.
    
    Args:
        texts: List of text strings to embed
        model_name: Name of the embedding model
        batch_size: Batch size for processing
        
    Returns:
        numpy array of embeddings
    """
    from sentence_transformers import SentenceTransformer
    
    # Map model names to sentence-transformer models
    model_mapping = {
        'bert-base-uncased': 'all-MiniLM-L6-v2',
        'roberta-base': 'all-mpnet-base-v2',
        'legal-bert': 'nlpaueb/legal-bert-base-uncased',
    }
    
    actual_model = model_mapping.get(model_name, 'all-MiniLM-L6-v2')
    
    logger.info(f"Loading embedding model: {actual_model}")
    model = SentenceTransformer(actual_model)
    
    logger.info(f"Generating embeddings for {len(texts)} texts")
    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=True,
        convert_to_numpy=True
    )
    
    return embeddings


def perform_clustering(
    embeddings: np.ndarray,
    method: str = 'agglomerative',
    **kwargs
) -> Tuple[np.ndarray, int]:
    """
    Perform clustering on embeddings.
    
    Args:
        embeddings: numpy array of embeddings
        method: Clustering method ('agglomerative', 'dbscan', 'kmeans', 'spectral')
        **kwargs: Additional parameters for the clustering algorithm
        
    Returns:
        Tuple of (cluster_labels, optimal_clusters)
    """
    n_samples = len(embeddings)
    
    if method == 'agglomerative':
        distance_threshold = kwargs.get('distance_threshold', None)
        n_clusters = kwargs.get('n_clusters', None)
        
        if distance_threshold is None and n_clusters is None:
            # Auto-determine optimal clusters using silhouette score
            n_clusters = _find_optimal_clusters(embeddings, max_clusters=min(10, n_samples - 1))
        
        clustering = AgglomerativeClustering(
            n_clusters=n_clusters,
            distance_threshold=distance_threshold,
            linkage='ward'
        )
        labels = clustering.fit_predict(embeddings)
        
    elif method == 'dbscan':
        eps = kwargs.get('eps', 0.5)
        min_samples = kwargs.get('min_samples', 2)
        
        clustering = DBSCAN(eps=eps, min_samples=min_samples, metric='cosine')
        labels = clustering.fit_predict(embeddings)
        
    elif method == 'kmeans':
        n_clusters = kwargs.get('n_clusters')
        if n_clusters is None:
            n_clusters = _find_optimal_clusters(embeddings, max_clusters=min(10, n_samples - 1))
        
        clustering = KMeans(
            n_clusters=n_clusters,
            max_iter=kwargs.get('max_iter', 300),
            random_state=42
        )
        labels = clustering.fit_predict(embeddings)
        
    elif method == 'spectral':
        n_clusters = kwargs.get('n_clusters')
        if n_clusters is None:
            n_clusters = _find_optimal_clusters(embeddings, max_clusters=min(10, n_samples - 1))
        
        clustering = SpectralClustering(
            n_clusters=n_clusters,
            affinity='nearest_neighbors',
            random_state=42
        )
        labels = clustering.fit_predict(embeddings)
        
    else:
        raise ValueError(f"Unknown clustering method: {method}")
    
    optimal_clusters = len(set(labels)) - (1 if -1 in labels else 0)
    
    return labels, optimal_clusters


def _find_optimal_clusters(embeddings: np.ndarray, max_clusters: int = 10) -> int:
    """Find optimal number of clusters using silhouette score."""
    best_score = -1
    best_k = 2
    
    for k in range(2, max_clusters + 1):
        try:
            kmeans = KMeans(n_clusters=k, random_state=42)
            labels = kmeans.fit_predict(embeddings)
            score = silhouette_score(embeddings, labels)
            
            if score > best_score:
                best_score = score
                best_k = k
        except Exception:
            continue
    
    return best_k


def calculate_clustering_metrics(
    embeddings: np.ndarray,
    labels: np.ndarray
) -> Dict[str, float]:
    """
    Calculate clustering quality metrics.
    
    Args:
        embeddings: numpy array of embeddings
        labels: Cluster labels
        
    Returns:
        Dictionary of metrics
    """
    # Filter out noise points (label -1) for metrics
    valid_mask = labels != -1
    if valid_mask.sum() < 2:
        return {'calinski_harabasz': 0.0, 'davies_bouldin': 0.0, 'silhouette': 0.0}
    
    valid_embeddings = embeddings[valid_mask]
    valid_labels = labels[valid_mask]
    
    n_clusters = len(set(valid_labels))
    if n_clusters < 2:
        return {'calinski_harabasz': 0.0, 'davies_bouldin': 0.0, 'silhouette': 0.0}
    
    return {
        'calinski_harabasz': calinski_harabasz_score(valid_embeddings, valid_labels),
        'davies_bouldin': davies_bouldin_score(valid_embeddings, valid_labels),
        'silhouette': silhouette_score(valid_embeddings, valid_labels)
    }


def generate_cluster_descriptions(
    cluster_texts: Dict[int, List[str]],
    api_key: Optional[str] = None,
    model: str = 'gpt-4o-mini'
) -> Dict[int, Dict[str, Any]]:
    """
    Generate AI descriptions for each cluster.

    Args:
        cluster_texts: Dictionary mapping cluster_id to list of texts in that cluster
        api_key: OpenAI API key
        model: LLM model to use

    Returns:
        Dictionary mapping cluster_id to description info
    """
    import os
    from openai import OpenAI

    api_key = api_key or os.environ.get('OPENAI_API_KEY')
    if not api_key:
        logger.warning("No OpenAI API key provided, skipping description generation")
        return {cid: {'label': f'Cluster {cid}', 'description': '', 'keywords': []}
                for cid in cluster_texts.keys()}

    client = OpenAI(api_key=api_key)
    descriptions = {}

    for cluster_id, texts in cluster_texts.items():
        # Sample texts for the prompt (limit to avoid token limits)
        sample_texts = texts[:5]
        combined_text = "\n\n---\n\n".join([t[:1000] for t in sample_texts])

        prompt = f"""Analyze the following documents that have been grouped together by a clustering algorithm.
Provide:
1. A short label (3-5 words) that describes what these documents have in common
2. A brief description (1-2 sentences) of the document type/category
3. 3-5 keywords that characterize this cluster

Documents:
{combined_text}

Respond in JSON format:
{{"label": "...", "description": "...", "keywords": ["...", "..."]}}"""

        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                max_tokens=200
            )

            import json
            result = json.loads(response.choices[0].message.content)
            descriptions[cluster_id] = {
                'label': result.get('label', f'Cluster {cluster_id}'),
                'description': result.get('description', ''),
                'keywords': result.get('keywords', [])
            }
        except Exception as e:
            logger.error(f"Error generating description for cluster {cluster_id}: {e}")
            descriptions[cluster_id] = {
                'label': f'Cluster {cluster_id}',
                'description': '',
                'keywords': []
            }

    return descriptions

