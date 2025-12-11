from typing import Protocol
from datetime import datetime
import uuid
import re

from pydantic import BaseModel


class VideoUploadedEvent(BaseModel):
    video_id: str
    filename: str
    bucket: str
    key: str
    uploaded_at: datetime


class VideoEventPublisher(Protocol):
    def publish_video_uploaded(self, event: VideoUploadedEvent) -> None:
        return


def sanitize_filename(filename: str) -> str:
    """Replace special characters with underscores for safe MinIO key generation."""
    return re.sub(r'[^a-zA-Z0-9._-]', '_', filename)


def handle_video_upload(
    storage_client: "StorageClient",
    publisher: VideoEventPublisher,
    filename: str,
    content: bytes,
) -> str:
    """
    Upload a video file to storage and publish an event.
    
    Args:
        storage_client: StorageClient for uploading to MinIO
        publisher: VideoEventPublisher for publishing the event
        filename: Original filename (will be sanitized in key)
        content: Raw file bytes
        
    Returns:
        video_id of the uploaded video
        
    Raises:
        ValueError: If file is empty
        Any exception from storage_client or publisher (caller should handle as 500)
    """
    if len(content) == 0:
        raise ValueError("File is empty")
    
    video_id = str(uuid.uuid4())
    safe_filename = sanitize_filename(filename)
    
    bucket = "therapy-videos"
    key = f"videos/{video_id}/{safe_filename}"
    
    storage_client.upload_file(bucket=bucket, key=key, content=content)
    
    event = VideoUploadedEvent(
        video_id=video_id,
        filename=filename,
        bucket=bucket,
        key=key,
        uploaded_at=datetime.now(),
    )
    publisher.publish_video_uploaded(event)
    
    return video_id
