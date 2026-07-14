import numpy as np
import logging
from transcripts.models import TranscriptChunk
from config.services.factory import get_embedding_provider

logger = logging.getLogger(__name__)

def compute_cosine_similarity(v1: list[float], v2: list[float]) -> float:
    """
    Computes cosine similarity between two vectors using numpy.
    """
    arr1 = np.array(v1, dtype=np.float32)
    arr2 = np.array(v2, dtype=np.float32)
    
    norm1 = np.linalg.norm(arr1)
    norm2 = np.linalg.norm(arr2)
    
    if norm1 == 0.0 or norm2 == 0.0:
        return 0.0
        
    dot_product = np.dot(arr1, arr2)
    return float(dot_product / (norm1 * norm2))

def semantic_search(query: str, video_ids: list[int], top_k: int = 5) -> list[dict]:
    """
    Performs semantic vector search across chunks for specified video IDs.
    Returns list of dicts with chunk object and similarity score.
    """
    logger.info(f"Performing semantic search for query: '{query}' across video IDs: {video_ids}")
    
    if not video_ids:
        return []

    # 1. Generate query embedding
    try:
        embedding_provider = get_embedding_provider()
        query_vector = embedding_provider.embed_text(query)
    except Exception as e:
        logger.error(f"Failed to generate query embedding: {e}")
        return []

    # 2. Fetch chunks belonging to the specified videos
    # We span: chunk -> transcript -> video -> id
    chunks = TranscriptChunk.objects.filter(
        transcript__video__id__in=video_ids,
        transcript__video__status="completed"
    ).select_related('transcript__video')

    scored_chunks = []
    
    # 3. Calculate similarity for each chunk in Python
    for chunk in chunks:
        chunk_vector = chunk.embedding
        if not chunk_vector:
            continue
            
        score = compute_cosine_similarity(query_vector, chunk_vector)
        scored_chunks.append({
            "chunk": chunk,
            "score": score
        })

    # 4. Sort by score descending and return top_k
    scored_chunks.sort(key=lambda x: x["score"], reverse=True)
    
    results = scored_chunks[:top_k]
    logger.info(f"Search complete. Found {len(results)} matches.")
    return results
