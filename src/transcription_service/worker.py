from src.audio_extractor_service.domain import AudioExtractedEvent
from src.transcription_service.domain import (
    TranscriptCreatedEvent,
    TranscriptionBackend,
    generate_transcript,
    StorageClient,
    TranscriptEventPublisher,
    VideosRepository,
)


def process_audio_extracted_event(
    event: AudioExtractedEvent,
    storage_client: StorageClient,
    backend: TranscriptionBackend,
    repository: VideosRepository,
    publisher: TranscriptEventPublisher,
) -> TranscriptCreatedEvent:
    """
    Process an AudioExtractedEvent by generating a transcript and publishing the result.

    Args:
        event: The AudioExtractedEvent to process.
        storage_client: The storage client to use.
        backend: The transcription backend to use.
        repository: The repository to update video status.
        publisher: The publisher to send the TranscriptCreatedEvent.

    Returns:
        The TranscriptCreatedEvent produced.
    """
    transcript_event = generate_transcript(event, backend, storage_client, repository)
    publisher.publish_transcript_created(transcript_event)

    return transcript_event
