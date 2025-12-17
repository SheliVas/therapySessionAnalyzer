from minio import Minio
import io

from src.shared.config import MinIOConfig


class MinioStorage:
    """MinIO implementation of StorageClient."""
    
    def __init__(self, config: MinIOConfig):
        """Initialize MinioStorage with configuration.
        
        Args:
            config: MinIOConfig with endpoint, access_key, secret_key.
        """
        self.config = config
        self.client = Minio(
            endpoint=config.endpoint,
            access_key=config.access_key,
            secret_key=config.secret_key,
            secure=config.secure,
        )
        self._bucket_exists_cache = {}
    
    def upload_file(self, bucket: str, key: str, content: bytes) -> None:
        """Upload a file to MinIO.
        
        Args:
            bucket: Bucket name.
            key: Object key (path within bucket).
            content: File content bytes.
        """
        if bucket not in self._bucket_exists_cache:
            self._bucket_exists_cache[bucket] = self.client.bucket_exists(bucket)
        
        if not self._bucket_exists_cache[bucket]:
            self.client.make_bucket(bucket)
            self._bucket_exists_cache[bucket] = True
        
        self.client.put_object(
            bucket_name=bucket,
            object_name=key,
            data=io.BytesIO(content),
            length=len(content),
        )
    
    def download_file(self, bucket: str, key: str) -> bytes:
        """Download a file from MinIO.
        
        Args:
            bucket: Bucket name.
            key: Object key (path within bucket).
            
        Returns:
            Raw bytes of the object.
            
        Raises:
            ValueError: If object is not found.
        """
        try:
            response = self.client.get_object(bucket, key)
            return response.read()
        except Exception as e:
            raise ValueError(f"Object not found: {bucket}/{key}") from e
