# Author: Faraniaina Rasolofoson - Exigent Group Limited
# Description: Variable declaration
# Adapted for aiDocuMines document_classification app

from enum import Enum
import os
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


class SummarizationMethod(Enum):
    OPENAI = "openai"
    BART = "facebook/bart-large-cnn"
    T5 = "t5-base"
    PEGASUS = "google/pegasus-xsum"
    SAULLM = "Equall/Saul-Instruct-v1"


class EmbeddingModelName(Enum):
    BERT_BASE_UNCASED = "bert-base-uncased"
    ROBERTA_BASE = "roberta-base"


class ClusteringMethod(Enum):
    AGGLOMERATIVE = "agglomerative"
    DBSCAN = "dbscan"
    OPTICS = "optics"
    AFFINITY_PROPAGATION = "affinity_propagation"
    SPECTRAL = "spectral"
    BIRCH = "birch"
    MEAN_SHIFT = "mean_shift"


class NbClusterMethod(Enum):
    SILHOUETTE = "silhouette"
    DENDROGRAM = "dendrogram"
    ELBOW = "elbow"


supported_file_types = [
    ".pdf",
    ".docx",
    ".pptx",
    ".xlsx",
    ".xlsm",
    ".txt",
    ".jpg",
    ".jpeg",
    ".png",
    ".mp4",
    ".rtf",
]

word_count_threshold = 1  # Minimum word count for a word to be considered for OpenAI query
additional_stop_words = ["shall", "will", "may", "herein", "upon", "among"]
openai_audio_model = "whisper-1"
audio_price_pm = 0.006

ai_model_params = {
    "model": os.environ.get("OPENAI_MODEL", "gpt-4-turbo"),
    "max_tokens": 3500,
    "limit_list_length": 17,  # The maximum number of fragments to be processed
    "input_price": 0.001,  # per 1K tokens
    "output_price": 0.003,  # per 1K tokens
}

summary_model = SummarizationMethod.OPENAI.value
embedding_model = EmbeddingModelName.BERT_BASE_UNCASED.value
clustering_method = ClusteringMethod.AGGLOMERATIVE.value
nb_cluster_method = NbClusterMethod.SILHOUETTE.value


@dataclass
class ClusteringConfig:
    """Configuration for document clustering - maintains compatibility with existing code."""

    # Clustering method
    clustering_method: str = 'agglomerative'

    # Embedding model
    embedding_model: str = 'bert-base-uncased'

    # Whether to generate AI descriptions for clusters
    generate_descriptions: bool = True

    # LLM settings for description generation
    llm_model: str = 'gpt-4o-mini'
    llm_api_key: Optional[str] = None

    # Clustering parameters
    min_cluster_size: int = 2
    max_clusters: Optional[int] = None
    distance_threshold: float = 0.5

    # DBSCAN specific
    dbscan_eps: float = 0.5
    dbscan_min_samples: int = 2

    # K-Means specific
    kmeans_n_clusters: Optional[int] = None
    kmeans_max_iter: int = 300

    # Spectral specific
    spectral_n_clusters: Optional[int] = None

    # File processing
    supported_extensions: List[str] = field(default_factory=lambda: supported_file_types)

    # Storage paths
    base_storage_path: str = '/tmp/document_classification'
    embeddings_subdir: str = 'embeddings'
    results_subdir: str = 'results'

    # Batch processing
    batch_size: int = 10
    max_concurrent_files: int = 5

    # Timeouts
    file_processing_timeout: int = 300  # 5 minutes per file
    total_timeout: int = 3600  # 1 hour total

    def __post_init__(self):
        """Initialize API key from environment if not provided."""
        if self.llm_api_key is None:
            self.llm_api_key = os.environ.get('OPENAI_API_KEY')

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'ClusteringConfig':
        """Create config from dictionary."""
        return cls(**{k: v for k, v in config_dict.items() if hasattr(cls, k)})

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return {
            'clustering_method': self.clustering_method,
            'embedding_model': self.embedding_model,
            'generate_descriptions': self.generate_descriptions,
            'llm_model': self.llm_model,
            'min_cluster_size': self.min_cluster_size,
            'max_clusters': self.max_clusters,
            'distance_threshold': self.distance_threshold,
            'dbscan_eps': self.dbscan_eps,
            'dbscan_min_samples': self.dbscan_min_samples,
            'kmeans_n_clusters': self.kmeans_n_clusters,
            'kmeans_max_iter': self.kmeans_max_iter,
            'spectral_n_clusters': self.spectral_n_clusters,
            'batch_size': self.batch_size,
            'max_concurrent_files': self.max_concurrent_files,
        }

    def get_storage_path(self, run_id: str, subdir: str = '') -> str:
        """Get storage path for a specific run."""
        path = os.path.join(self.base_storage_path, str(run_id), subdir)
        os.makedirs(path, exist_ok=True)
        return path

    def is_supported_file(self, filename: str) -> bool:
        """Check if file extension is supported."""
        ext = os.path.splitext(filename)[1].lower()
        return ext in self.supported_extensions

