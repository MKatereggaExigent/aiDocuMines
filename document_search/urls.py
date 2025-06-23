# document_search/urls.py

from django.urls import path
from document_search import views

urlpatterns = [
    # ──────────── 🔍 Search & Results ─────────────
    path("search/", views.ChunkedFileSearchView.as_view(), name="vector-search"),

    # ──────────── 📦 Vectorized Chunk Data ────────
    path("chunks/", views.VectorChunkListView.as_view(), name="chunk-list"),  # admin only

    # ──────────── ⚙️ Trigger Vectorization ────────
    path("index/", views.TriggerVectorIndexingView.as_view(), name="vector-index"),         # POST {file_ids, force}
    path("reindex-missing/", views.BulkReindexMissingView.as_view(), name="bulk-reindex"),  # POST (admin only)
]

