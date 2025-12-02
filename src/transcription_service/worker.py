from pathlib import Path

from src.audio_extractor_service.domain import AudioExtractedEvent
from src.transcription_service.domain import (
    TranscriptCreatedEvent,
    TranscriptionBackend,
    generate_transcript,
)


class TranscriptEventPublisher:
    """Interface for publishing transcript created events."""

    def publish_transcript_created(self, event: TranscriptCreatedEvent) -> None:
        """Publish a TranscriptCreatedEvent."""
        raise NotImplementedError


def process_audio_extracted_event(
    event: AudioExtractedEvent,
    base_output_dir: Path,
    backend: TranscriptionBackend,
    publisher: TranscriptEventPublisher,
) -> TranscriptCreatedEvent:
    """
    Process an AudioExtractedEvent by generating a transcript and publishing the result.

    Args:
        event: The AudioExtractedEvent to process.
        base_output_dir: The base directory to write transcripts to.
        backend: The transcription backend to use.
        publisher: The publisher to send the TranscriptCreatedEvent.

    Returns:
        The TranscriptCreatedEvent produced.
    """
    transcript_event = generate_transcript(event, backend, base_output_dir)
    publisher.publish_transcript_created(transcript_event)

    return transcript_event
