import os
import re

from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings

_embeddings = None


def _get_embeddings():
    """Create embeddings lazily so local imports do not require OpenAI credentials."""
    global _embeddings
    if _embeddings is not None:
        return _embeddings

    if not os.getenv("OPENAI_API_KEY"):
        return None

    _embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    return _embeddings

# In-memory FAISS stores for the hackathon
jd_store = None
candidate_store = None
fallback_jd_texts = {}

STOPWORDS = {
    "and",
    "or",
    "the",
    "a",
    "an",
    "to",
    "for",
    "with",
    "of",
    "in",
    "on",
    "at",
    "by",
    "from",
    "years",
    "year",
    "experience",
    "role",
    "team",
    "teams",
    "engineer",
    "developer",
    "development",
    "work",
    "working",
    "skill",
    "skills",
    "responsibilities",
    "required",
    "preferred",
}

TOKEN_SYNONYMS = {
    "lead": "leadership",
    "leader": "leadership",
    "leading": "leadership",
    "cloud": "aws",
    "dockerized": "docker",
    "fastapi": "fastapi",
    "fast": "fastapi",
    "api": "fastapi",
}


def _token_set(text: str):
    tokens = set()
    for token in re.sub(r"[^\w\s]", " ", text.lower()).split():
        normalized = TOKEN_SYNONYMS.get(token, token)
        if normalized and normalized not in STOPWORDS:
            tokens.add(normalized)
    return tokens


def _fallback_similarity(jd_text: str, candidate_summary: str) -> float:
    jd_tokens = _token_set(jd_text)
    candidate_tokens = _token_set(candidate_summary)

    if not jd_tokens or not candidate_tokens:
        return 0.0

    overlap = jd_tokens & candidate_tokens
    jd_coverage = len(overlap) / len(jd_tokens)
    candidate_precision = len(overlap) / len(candidate_tokens)

    # Reward both recall against the JD and precision against the resume summary.
    score = (jd_coverage * 0.6 + candidate_precision * 0.35 + (len(overlap) > 0) * 0.05) * 100.0

    # Give a small boost for strong signal keywords that matter in recruiting.
    high_value_keywords = {"python", "fastapi", "aws", "docker", "kubernetes", "leadership"}
    keyword_hits = len(overlap & high_value_keywords)
    score += min(15.0, keyword_hits * 3.0)

    return round(min(100.0, score), 2)

def index_job_description(jd_id: str, traits_and_skills: str):
    global jd_store
    embeddings = _get_embeddings()
    if embeddings is None:
        fallback_jd_texts[jd_id] = traits_and_skills
        return

    if jd_store is None:
        jd_store = FAISS.from_texts([traits_and_skills], embeddings, metadatas=[{"id": jd_id}])
    else:
        jd_store.add_texts([traits_and_skills], metadatas=[{"id": jd_id}])

def index_candidate(candidate_id: str, candidate_summary: str):
    global candidate_store
    embeddings = _get_embeddings()
    if embeddings is None:
        return

    if candidate_store is None:
        candidate_store = FAISS.from_texts([candidate_summary], embeddings, metadatas=[{"id": candidate_id}])
    else:
        candidate_store.add_texts([candidate_summary], metadatas=[{"id": candidate_id}])

def calculate_semantic_match(jd_id: str, candidate_summary: str) -> float:
    # A simple way to score is to embed the candidate summary and search the JD store
    # FAISS returns L2 distance. We invert it for a "similarity score" out of 100.
    embeddings = _get_embeddings()
    if embeddings is None:
        jd_text = fallback_jd_texts.get(jd_id, "")
        return _fallback_similarity(jd_text, candidate_summary)

    if jd_store is None:
        return 0.0
    
    docs_and_scores = jd_store.similarity_search_with_score(candidate_summary, k=1)
    if not docs_and_scores:
        return 0.0
        
    _, distance = docs_and_scores[0]
    # Convert L2 distance to a pseudo-percentage (lower distance = higher match)
    match_score = max(0.0, 100.0 - (distance * 50)) 
    return round(match_score, 2)