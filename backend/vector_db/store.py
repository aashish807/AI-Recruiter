import os
import shutil
import numpy as np
from typing import List, Dict, Any, Tuple
from langchain_community.vectorstores import FAISS
from langchain_core.embeddings import Embeddings

# Base path for disk persistence
INDICES_DIR = os.path.join(os.path.dirname(__file__), "indices")

class DummyEmbeddings(Embeddings):
    """Placeholder embedding class to satisfy LangChain parameters without calling APIs."""
    def __init__(self, dimension: int):
        self.dimension = dimension
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [[0.0] * self.dimension for _ in texts]
    def embed_query(self, text: str) -> List[float]:
        return [0.0] * self.dimension

# In-memory caches for the FAISS aspect stores
_stores: Dict[str, FAISS] = {}

def _normalize_vector(vector: List[float]) -> List[float]:
    """L2 normalizes a vector list so FAISS searches resolve to Cosine Similarity."""
    arr = np.array(vector, dtype=np.float32)
    norm = np.linalg.norm(arr)
    if norm > 0:
        arr = arr / norm
    return arr.tolist()

def _get_aspect_path(aspect: str) -> str:
    return os.path.join(INDICES_DIR, f"{aspect}_index")

def _load_store(aspect: str, dimension: int) -> FAISS:
    """Helper to load a FAISS aspect index from disk, or initialize if missing."""
    global _stores
    if aspect in _stores and _stores[aspect] is not None:
        return _stores[aspect]

    path = _get_aspect_path(aspect)
    dummy_emb = DummyEmbeddings(dimension)

    if os.path.exists(path) and os.path.exists(os.path.join(path, "index.faiss")):
        try:
            store = FAISS.load_local(path, dummy_emb, allow_dangerous_deserialization=True)
            _stores[aspect] = store
            return store
        except Exception as e:
            print(f"Warning: Failed to load index for '{aspect}' from disk. Resetting: {e}")

    _stores[aspect] = None
    return None

def add_candidate_vectors(candidate_id: str, aspect_vectors: Dict[str, List[float]]):
    """Indexes and saves unit-normalized multi-aspect vectors for a candidate."""
    os.makedirs(INDICES_DIR, exist_ok=True)

    for aspect, vector in aspect_vectors.items():
        if not vector:
            continue
            
        dimension = len(vector)
        normalized_vector = _normalize_vector(vector)
        path = _get_aspect_path(aspect)
        
        # Unique representation tag
        text_rep = f"candidate_id:{candidate_id}"
        metadatas = [{"candidate_id": candidate_id}]

        store = _load_store(aspect, dimension)
        if store is None:
            # Initialize new store
            dummy_emb = DummyEmbeddings(dimension)
            store = FAISS.from_embeddings([(text_rep, normalized_vector)], dummy_emb, metadatas=metadatas)
        else:
            # Add to existing store
            store.add_embeddings([(text_rep, normalized_vector)], metadatas=metadatas)

        # Cache in memory and save to disk
        _stores[aspect] = store
        store.save_local(path)

def search_aspect_vectors(aspect: str, query_vector: List[float], k: int = 100) -> List[Tuple[str, float]]:
    """Queries a specific FAISS index and returns sorted Candidate IDs with Cosine Similarity scores."""
    if not query_vector:
        return []

    dimension = len(query_vector)
    store = _load_store(aspect, dimension)
    if store is None:
        return []

    normalized_query = _normalize_vector(query_vector)
    
    # Query FAISS
    docs_and_scores = store.similarity_search_with_score_by_vector(normalized_query, k=k)

    
    results = []
    for doc, dist in docs_and_scores:
        cand_id = doc.metadata.get("candidate_id")
        if not cand_id:
            continue
            
        # Cosine Similarity score from L2 distance of normalized vectors:
        # L2 Distance squared = 2 - 2 * Cos_Sim -> Cos_Sim = 1 - Dist / 2
        cos_sim = 1.0 - (dist / 2.0)
        score_percent = max(0.0, min(100.0, cos_sim * 100.0))
        results.append((cand_id, round(float(score_percent), 2)))

        
    # Return sorted results by similarity score
    return sorted(results, key=lambda x: x[1], reverse=True)

def reset_vector_database():
    """Wipes all indexes from filesystem and memory."""
    global _stores
    _stores.clear()
    if os.path.exists(INDICES_DIR):
        shutil.rmtree(INDICES_DIR)
