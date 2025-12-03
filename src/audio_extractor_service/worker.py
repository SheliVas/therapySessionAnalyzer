from pathlib import Path

from src.upload_service.domain import VideoUploadedEvent
from src.audio_extractor_service.domain import (
    AudioExtractedEvent,
    handle_video_uploaded,
)


class AudioEventPublisher:
    def publish_audio_extracted(self, event: AudioExtractedEvent) -> None:
        """Interface method – concrete implementations will send the event somewhere."""
        raise NotImplementedError


def process_video_uploaded_event(
    event: VideoUploadedEvent,
    base_output_dir: Path,
    publisher: AudioEventPublisher,
) -> AudioExtractedEvent:
    
    audio_event = handle_video_uploaded(event, base_output_dir)
    publisher.publish_audio_extracted(audio_event)

    return audio_event
