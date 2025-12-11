from src.audio_extractor_service.domain import AudioExtractedEvent
from src.transcription_service.domain import (
    TranscriptCreatedEvent,
    TranscriptionBackend,
    generate_transcript,
    StorageClient,
)


class TranscriptEventPublisher:
    def publish_transcript_created(self, event: TranscriptCreatedEvent) -> None:
        raise NotImplementedError


def process_audio_extracted_event(
    event: AudioExtractedEvent,
    storage_client: StorageClient,
    backend: TranscriptionBackend,
    publisher: TranscriptEventPublisher,
) -> TranscriptCreatedEvent:
    """
    Process an AudioExtractedEvent by generating a transcript and publishing the result.

    Args:
        event: The AudioExtractedEvent to process.
        storage_client: The storage client to use.
        backend: The transcription backend to use.
        publisher: The publisher to send the TranscriptCreatedEvent.

    Returns:
        The TranscriptCreatedEvent produced.
    """
    transcript_event = generate_transcript(event, backend, storage_client)
    publisher.publish_transcript_created(transcript_event)

    return transcript_event
