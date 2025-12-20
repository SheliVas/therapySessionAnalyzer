from abc import ABC, abstractmethod
from typing import Protocol

from pydantic import BaseModel

from src.shared.protocols import StorageClient, VideosRepository
from src.audio_extractor_service.domain import AudioExtractedEvent


class TranscriptionError(Exception):
    """Base exception for transcription errors."""
    pass


class TranscriptCreatedEvent(BaseModel):
    video_id: str
    bucket: str
    key: str


class TranscriptEventPublisher(Protocol):
    def publish_transcript_created(self, event: TranscriptCreatedEvent) -> None:
        ...


class TranscriptionBackend(ABC):
    @abstractmethod
    def transcribe(self, audio_bytes: bytes) -> str:
        """Transcribe audio bytes and return the transcript text."""
        ...


def generate_transcript(
    event: AudioExtractedEvent,
    backend: TranscriptionBackend,
    storage_client: StorageClient,
    repository: VideosRepository,
) -> TranscriptCreatedEvent:
    """
    Generate a transcript from an audio file.

    Args:
        event: The AudioExtractedEvent containing the audio bucket/key.
        backend: The transcription backend to use.
        storage_client: The storage client to download audio and upload transcript.
        repository: The repository to update video status.

    Returns:
        A TranscriptCreatedEvent with the bucket/key to the transcript file.
    """
    audio_bytes = storage_client.download_file(bucket=event.bucket, key=event.key)
    
    if not audio_bytes:
        raise ValueError("Downloaded audio is empty")

    transcript_text = backend.transcribe(audio_bytes)

    transcript_bucket = "therapy-transcripts"
    transcript_key = f"transcripts/{event.video_id}/transcript.txt"
    
    storage_client.upload_file(
        bucket=transcript_bucket,
        key=transcript_key,
        content=transcript_text.encode("utf-8")
    )

    transcript_path = f"{transcript_bucket}/{transcript_key}"
    repository.mark_transcribed(video_id=event.video_id, transcript_path=transcript_path)

    return TranscriptCreatedEvent(
        video_id=event.video_id,
        bucket=transcript_bucket,
        key=transcript_key,
    )
