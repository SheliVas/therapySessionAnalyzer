from abc import ABC, abstractmethod

from pydantic import BaseModel

from src.transcription_service.domain import TranscriptCreatedEvent
from src.analysis_service.domain import AnalysisBackend, analyze_transcript, StorageClient


class AnalysisCompletedEvent(BaseModel):
    video_id: str
    word_count: int
    extra: dict = {}


class AnalysisEventPublisher(ABC):
    @abstractmethod
    def publish_analysis_completed(self, event: AnalysisCompletedEvent) -> None:
        """Publish an AnalysisCompletedEvent."""
        ...


class AnalysisRepository(ABC):
    @abstractmethod
    def save_analysis(self, event: AnalysisCompletedEvent) -> None:
        """Save an AnalysisCompletedEvent to the repository."""
        ...


class VideosRepository(ABC):
    @abstractmethod
    def mark_analyzed(self, video_id: str, word_count: int) -> None:
        """Mark a video as analyzed with word count."""
        ...


def process_transcript_created_event(
    event: TranscriptCreatedEvent,
    backend: AnalysisBackend,
    publisher: AnalysisEventPublisher,
    repository: AnalysisRepository,
    storage_client: StorageClient,
    videos_repository: VideosRepository,
) -> AnalysisCompletedEvent:
    """Process a TranscriptCreatedEvent and publish an AnalysisCompletedEvent.

    Args:
        event: The TranscriptCreatedEvent to process.
        backend: The analysis backend to use.
        publisher: The event publisher to use.
        repository: The repository to save the analysis to.
        storage_client: The storage client to download the transcript.
        videos_repository: The videos repository to mark analysis status.

    Returns:
        The AnalysisCompletedEvent that was published and saved.
    """
    analysis_result = analyze_transcript(event, backend, storage_client)
    completed_event = AnalysisCompletedEvent(
        video_id=analysis_result.video_id,
        word_count=analysis_result.word_count,
        extra=analysis_result.extra,
    )
    
    videos_repository.mark_analyzed(analysis_result.video_id, analysis_result.word_count)
    
    repository.save_analysis(completed_event)
    publisher.publish_analysis_completed(completed_event)
    return completed_event
