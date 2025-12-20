import logging

from src.shared.protocols import StorageClient, VideosRepository
from src.transcription_service.domain import TranscriptCreatedEvent
from src.analysis_service.domain import (
    AnalysisBackend,
    AnalysisCompletedEvent,
    AnalysisEventPublisher,
    AnalysisRepository,
    analyze_transcript,
)

logger = logging.getLogger(__name__)


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
    logger.info("worker.process start video_id=%s", event.video_id)
    analysis_result = analyze_transcript(event, backend, storage_client)
    completed_event = AnalysisCompletedEvent(
        video_id=analysis_result.video_id,
        word_count=analysis_result.word_count,
        analysis=analysis_result.analysis,
    )
    
    videos_repository.mark_analyzed(analysis_result.video_id, analysis_result.word_count)
    logger.info(
        "worker.persisted video_id=%s word_count=%d",
        analysis_result.video_id,
        analysis_result.word_count,
    )
    
    repository.save_analysis(completed_event)
    logger.info("worker.analysis.saved video_id=%s", analysis_result.video_id)
    publisher.publish_analysis_completed(completed_event)
    logger.info("worker.analysis.published video_id=%s", analysis_result.video_id)
    return completed_event
