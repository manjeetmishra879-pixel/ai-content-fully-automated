"""
Vector database client initialization (Chroma/Qdrant)
"""

from app.core.config import settings

# Vector DB initialization based on config
# Supports Chroma and Qdrant

def get_vector_db():
    """Get vector database client based on configuration"""
    if settings.vector_db_type == "chroma":
        try:
            import chromadb
            client = chromadb.PersistentClient(path="./chroma_db")
            return client
        except ImportError:
            raise ImportError("chromadb not installed. Install with: pip install chromadb")
    elif settings.vector_db_type == "qdrant":
        try:
            from qdrant_client import QdrantClient
            client = QdrantClient(url=settings.qdrant_url)
            return client
        except ImportError:
            raise ImportError("qdrant-client not installed. Install with: pip install qdrant-client")
    else:
        raise ValueError(f"Unsupported vector DB: {settings.vector_db_type}")


def get_embedding_model():
    """Get sentence transformer model for embeddings"""
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer('all-MiniLM-L6-v2')
        return model
    except ImportError:
        raise ImportError("sentence-transformers not installed. Install with: pip install sentence-transformers")
