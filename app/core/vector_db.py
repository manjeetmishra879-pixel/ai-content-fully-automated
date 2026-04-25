"""
Vector database client initialization (Chroma/Qdrant)
"""

from app.core.config import settings

# Vector DB initialization based on config
# Supports Chroma and Qdrant

def get_vector_db():
    """Get vector database client based on configuration"""
    if settings.vector_db_type == "chroma":
        # Initialize Chroma
        pass
    elif settings.vector_db_type == "qdrant":
        # Initialize Qdrant
        pass
    else:
        raise ValueError(f"Unsupported vector DB: {settings.vector_db_type}")
