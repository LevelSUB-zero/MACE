"""
Sentence Embedder for NLU

Uses sentence-transformers for fast, lightweight embeddings.
"""
import os
from typing import List, Union
import numpy as np

# Lazy import to avoid loading model on module import
_model = None
_model_name = None


def get_embedder(model_name: str = None):
    """
    Get or initialize the sentence embedder.
    
    Args:
        model_name: Model to use (default: from config)
    
    Returns:
        SentenceTransformer model
    """
    global _model, _model_name
    
    if model_name is None:
        from .config import EMBEDDER_MODEL
        model_name = EMBEDDER_MODEL
    
    if _model is None or _model_name != model_name:
        try:
            from sentence_transformers import SentenceTransformer
            print(f"Loading embedder: {model_name}...")
            _model = SentenceTransformer(model_name)
            _model_name = model_name
            print(f"Embedder loaded successfully")
        except ImportError:
            raise ImportError(
                "sentence-transformers not installed. "
                "Run: pip install sentence-transformers"
            )
    
    return _model


def embed(texts: Union[str, List[str]], normalize: bool = True) -> np.ndarray:
    """
    Embed text(s) into vectors.
    
    Args:
        texts: Single string or list of strings
        normalize: Whether to L2m-normalize embeddings
    
    Returns:
        numpy array of shape (n_texts, embedding_dim)
    """
    model = get_embedder()
    
    if isinstance(texts, str):
        texts = [texts]
    
    embeddings = model.encode(
        texts,
        convert_to_numpy=True,
        normalize_embeddings=normalize,
        show_progress_bar=False
    )
    
    return embeddings


def embed_single(text: str, normalize: bool = True) -> np.ndarray:
    """Embed a single text and return 1D array."""
    return embed(text, normalize)[0]


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine similarity between two vectors."""
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
