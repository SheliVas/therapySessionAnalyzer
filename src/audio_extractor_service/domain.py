from typing import Protocol

from pydantic import BaseModel

from src.upload_service.domain import VideoUploadedEvent


class StorageClient(Protocol):
    """Protocol for storage client (MinIO, S3, etc.)."""
    
    def download_file(self, bucket: str, key: str) -> bytes:
        """Download file from storage."""
        ...
    
    def upload_file(self, bucket: str, key: str, content: bytes) -> None:
        """Upload file to storage."""
        ...


class AudioConverter(Protocol):
    """Protocol for audio conversion."""
    
    def convert(self, video_bytes: bytes) -> bytes:
        """Convert video bytes to audio bytes."""
        ...


class AudioExtractedEvent(BaseModel):
    video_id: str
    bucket: str
    key: str


class AudioEventPublisher(Protocol):
    """Protocol for publishing audio extraction events."""
    
    def publish_audio_extracted(self, event: AudioExtractedEvent) -> None:
        """Publish an audio extracted event."""
        ...


def extract_audio_from_video_event(
    event: VideoUploadedEvent,
    storage_client: StorageClient,
    audio_converter: AudioConverter,
) -> AudioExtractedEvent:
    """
    Extract audio from a video in MinIO storage.
    
    Args:
        event: VideoUploadedEvent with bucket/key of the video file.
        storage_client: Client to download from/upload to storage.
        audio_converter: Converter to extract audio from video bytes.
        
    Returns:
        AudioExtractedEvent with bucket/key of the extracted MP3.
        
    Raises:
        ValueError: If video bytes are empty.
    """
    video_bytes = storage_client.download_file(bucket=event.bucket, key=event.key)
    
    if len(video_bytes) == 0:
        raise ValueError("Downloaded video file is empty")
    
    audio_bytes = audio_converter.convert(video_bytes)
    audio_key = f"audio/{event.video_id}/audio.mp3"
    storage_client.upload_file(bucket="therapy-audio", key=audio_key, content=audio_bytes)
    
    return AudioExtractedEvent(
        video_id=event.video_id,
        bucket="therapy-audio",
        key=audio_key,
    )


def handle_audio_extraction_event(
    event: VideoUploadedEvent,
    storage_client: StorageClient,
    audio_converter: AudioConverter,
    publisher: AudioEventPublisher,
) -> None:
    """
    Handle video upload event: extract audio and publish result.
    
    Args:
        event: VideoUploadedEvent.
        storage_client: Client for storage operations.
        audio_converter: Converter for audio extraction.
        publisher: Publisher for AudioExtractedEvent.
    """
    audio_event = extract_audio_from_video_event(
        event=event,
        storage_client=storage_client,
        audio_converter=audio_converter,
    )
    publisher.publish_audio_extracted(audio_event)


