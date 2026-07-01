from typing import List, Tuple
from embeddings.generator import EmbeddingGenerator
from vector_db.store import search_aspect_vectors

# Global instances loaded lazily
_generator = None

def _get_generator() -> EmbeddingGenerator:
    global _generator
    if _generator is None:
        _generator = EmbeddingGenerator()
    return _generator

def search_candidates(job_description_text: str, k: int = 100) -> List[Tuple[str, float]]:
    """Generates the JD query embedding and retrieves candidate IDs with similarity scores from FAISS."""
    if not job_description_text or not job_description_text.strip():
        return []

    generator = _get_generator()
    
    # 1. Embed job description text
    query_vector = generator.embed_text(job_description_text)
    
    # 2. Query the core resume FAISS vector index
    results = search_aspect_vectors("resume", query_vector, k=k)
    
    return results
