from src.shared.protocols import StorageClient, VideosRepository
from src.upload_service.domain import VideoUploadedEvent
from src.audio_extractor_service.domain import (
    AudioEventPublisher,
    AudioConverter,
    handle_audio_extraction_event,
)


def process_video_uploaded_event(
    event: VideoUploadedEvent,
    storage_client: StorageClient,
    audio_converter: AudioConverter,
    repository: VideosRepository,
    publisher: AudioEventPublisher,
) -> None:
    """
    Process a video uploaded event: extract audio and publish result.
    
    Args:
        event: VideoUploadedEvent from upload service.
        storage_client: Client for MinIO/storage operations.
        audio_converter: Converter for audio extraction.
        repository: Repository for status updates.
        publisher: Publisher for audio extraction events.
    """
    handle_audio_extraction_event(
        event=event,
        storage_client=storage_client,
        audio_converter=audio_converter,
        repository=repository,
        publisher=publisher,
    )
