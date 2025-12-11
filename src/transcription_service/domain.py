from abc import ABC, abstractmethod
from typing import Protocol

from pydantic import BaseModel

from src.audio_extractor_service.domain import AudioExtractedEvent


class TranscriptCreatedEvent(BaseModel):
    video_id: str
    bucket: str
    key: str


class StorageClient(Protocol):
    def download_file(self, bucket: str, key: str) -> bytes:
        ...

    def upload_file(self, bucket: str, key: str, content: bytes) -> None:
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
) -> TranscriptCreatedEvent:
    """
    Generate a transcript from an audio file.

    Args:
        event: The AudioExtractedEvent containing the audio bucket/key.
        backend: The transcription backend to use.
        storage_client: The storage client to download audio and upload transcript.

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

    return TranscriptCreatedEvent(
        video_id=event.video_id,
        bucket=transcript_bucket,
        key=transcript_key,
    )
