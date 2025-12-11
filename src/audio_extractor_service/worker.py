from src.upload_service.domain import VideoUploadedEvent
from src.audio_extractor_service.domain import (
    AudioExtractedEvent,
    AudioEventPublisher,
    StorageClient,
    AudioConverter,
    handle_audio_extraction_event,
)


def process_video_uploaded_event(
    event: VideoUploadedEvent,
    storage_client: StorageClient,
    audio_converter: AudioConverter,
    publisher: AudioEventPublisher,
) -> AudioExtractedEvent:
    """
    Process a video uploaded event: extract audio and publish result.
    
    Args:
        event: VideoUploadedEvent from upload service.
        storage_client: Client for MinIO/storage operations.
        audio_converter: Converter for audio extraction.
        publisher: Publisher for audio extraction events.
        
    Returns:
        AudioExtractedEvent with extraction result.
    """
    from src.audio_extractor_service.domain import extract_audio_from_video_event
    
    audio_event = extract_audio_from_video_event(
        event=event,
        storage_client=storage_client,
        audio_converter=audio_converter,
    )
    
    publisher.publish_audio_extracted(audio_event)
    
    return audio_event
