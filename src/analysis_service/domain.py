from abc import ABC, abstractmethod
import logging

from pydantic import BaseModel

from src.shared.protocols import StorageClient
from src.transcription_service.domain import TranscriptCreatedEvent

logger = logging.getLogger(__name__)


class AnalysisResult(BaseModel):
    video_id: str
    word_count: int
    analysis: dict = {}


class AnalysisCompletedEvent(BaseModel):
    """Event published when analysis is complete."""
    video_id: str
    word_count: int
    analysis: dict = {}


class AnalysisEventPublisher(ABC):
    """Protocol for publishing analysis events."""

    @abstractmethod
    def publish_analysis_completed(self, event: "AnalysisCompletedEvent") -> None:
        """Publish an AnalysisCompletedEvent."""
        ...


class AnalysisRepository(ABC):
    """Protocol for persisting analysis results."""

    @abstractmethod
    def save_analysis(self, event: "AnalysisCompletedEvent") -> None:
        """Save an AnalysisCompletedEvent to the repository."""
        ...


class AnalysisBackend(ABC):

    @abstractmethod
    def analyze(self, transcript_text: str, video_id: str) -> AnalysisResult:
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
    logger.info(
        "analysis.start event received video_id=%s bucket=%s key=%s",
        event.video_id,
        event.bucket,
        event.key,
    )
    transcript_bytes = storage_client.download_file(bucket=event.bucket, key=event.key)
    logger.info(
        "analysis.transcript.downloaded video_id=%s bytes=%d",
        event.video_id,
        len(transcript_bytes),
    )
    transcript_text = transcript_bytes.decode("utf-8")
    
    result = backend.analyze(transcript_text, video_id=event.video_id)

    if result.video_id != event.video_id:
        result = AnalysisResult(
            video_id=event.video_id,
            word_count=result.word_count,
            analysis=result.analysis,
        )
    logger.info(
        "analysis.completed video_id=%s word_count=%d",
        result.video_id,
        result.word_count,
    )
    return result
