from typing import Protocol

from pydantic import BaseModel

from src.shared.protocols import StorageClient, VideosRepository
from src.upload_service.domain import VideoUploadedEvent


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
    repository: VideosRepository,
) -> AudioExtractedEvent:
    """
    Extract audio from a video and update repository status.
    
    Args:
        event: VideoUploadedEvent with bucket/key of the video file.
        storage_client: Client to download from/upload to storage.
        audio_converter: Converter to extract audio from video bytes.
        repository: Repository to update video status.
        
    Returns:
        AudioExtractedEvent with bucket/key of the extracted MP3.
        
    Raises:
        ValueError: If video bytes are empty or video_id is empty.
        VideoNotFoundError: If repository update fails.
    """
    if not event.video_id:
        raise ValueError("Video ID cannot be empty")
    
    video_bytes = storage_client.download_file(bucket=event.bucket, key=event.key)
    
    if len(video_bytes) == 0:
        raise ValueError("Downloaded video file is empty")
    
    audio_bytes = audio_converter.convert(video_bytes)
    audio_key = f"audio/{event.video_id}/audio.mp3"
    storage_client.upload_file(bucket="therapy-audio", key=audio_key, content=audio_bytes)
    
    audio_path = f"therapy-audio/{audio_key}"
    repository.mark_audio_extracted(video_id=event.video_id, audio_path=audio_path)
    
    return AudioExtractedEvent(
        video_id=event.video_id,
        bucket="therapy-audio",
        key=audio_key,
    )


def handle_audio_extraction_event(
    event: VideoUploadedEvent,
    storage_client: StorageClient,
    audio_converter: AudioConverter,
    repository: VideosRepository,
    publisher: AudioEventPublisher,
) -> None:
    """
    Handle video upload event: extract audio, update repository, and publish result.
    
    Args:
        event: VideoUploadedEvent.
        storage_client: Client for storage operations.
        audio_converter: Converter for audio extraction.
        repository: Repository for status updates.
        publisher: Publisher for AudioExtractedEvent.
    """
    audio_event = extract_audio_from_video_event(
        event=event,
        storage_client=storage_client,
        audio_converter=audio_converter,
        repository=repository,
    )
    publisher.publish_audio_extracted(audio_event)


