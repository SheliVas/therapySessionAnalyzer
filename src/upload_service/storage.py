from typing import Protocol


class StorageClient(Protocol):
    """Abstract interface for file storage (MinIO, S3, etc.)."""
    
    def upload_file(
        self,
        bucket: str,
        key: str,
        content: bytes,
    ) -> None:
        """Upload a file to storage.
        
        Args:
            bucket: Bucket/container name.
            key: Object key (path within bucket).
            content: File content bytes.
        """
        ...
