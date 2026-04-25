"""
MinIO object storage client initialization
"""

from minio import Minio
from app.core.config import settings

minio_client = Minio(
    settings.minio_endpoint,
    access_key=settings.minio_access_key,
    secret_key=settings.minio_secret_key,
    secure=settings.minio_secure,
)

def get_minio():
    """Get MinIO client instance"""
    return minio_client
