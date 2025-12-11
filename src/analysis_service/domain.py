from abc import ABC, abstractmethod
from typing import Protocol

from pydantic import BaseModel

from src.transcription_service.domain import TranscriptCreatedEvent


class AnalysisResult(BaseModel):
    video_id: str
    word_count: int
    extra: dict = {}


class StorageClient(Protocol):
    def download_file(self, bucket: str, key: str) -> bytes:
        ...


class AnalysisBackend(ABC):

    @abstractmethod
    def analyze(self, transcript_text: str) -> AnalysisResult:
        """Analyze the given transcript text and return an AnalysisResult."""
        ...


def analyze_transcript(
    event: TranscriptCreatedEvent,
    backend: AnalysisBackend,
    storage_client: StorageClient,
) -> AnalysisResult:
    """Analyze a transcript from a TranscriptCreatedEvent.

    Args:
        event: The TranscriptCreatedEvent containing the transcript bucket/key.
        backend: The analysis backend to use.
        storage_client: The storage client to download the transcript.

    Returns:
        The AnalysisResult from the backend.
    """
    transcript_bytes = storage_client.download_file(bucket=event.bucket, key=event.key)
    transcript_text = transcript_bytes.decode("utf-8")
    
    result = backend.analyze(transcript_text)

    if result.video_id != event.video_id:
        result = AnalysisResult(
            video_id=event.video_id,
            word_count=result.word_count,
            extra=result.extra,
        )
    return result