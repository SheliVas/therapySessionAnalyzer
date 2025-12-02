from abc import ABC, abstractmethod

from pydantic import BaseModel

from src.transcription_service.domain import TranscriptCreatedEvent
from src.analysis_service.domain import AnalysisBackend, analyze_transcript


class AnalysisCompletedEvent(BaseModel):
    video_id: str
    word_count: int
    extra: dict = {}


class AnalysisEventPublisher(ABC):
    @abstractmethod
    def publish_analysis_completed(self, event: AnalysisCompletedEvent) -> None:
        """Publish an AnalysisCompletedEvent."""
        ...


def process_transcript_created_event(
    event: TranscriptCreatedEvent,
    backend: AnalysisBackend,
    publisher: AnalysisEventPublisher,
) -> AnalysisCompletedEvent:
    """Process a TranscriptCreatedEvent and publish an AnalysisCompletedEvent.

    Args:
        event: The TranscriptCreatedEvent to process.
        backend: The analysis backend to use.
        publisher: The event publisher to use.

    Returns:
        The AnalysisCompletedEvent that was published.
    """
    analysis_result = analyze_transcript(event, backend)
    completed_event = AnalysisCompletedEvent(
        video_id=analysis_result.video_id,
        word_count=analysis_result.word_count,
        extra=analysis_result.extra,
    )
    publisher.publish_analysis_completed(completed_event)
    return completed_event
