from abc import ABC, abstractmethod
from pathlib import Path

from pydantic import BaseModel

from src.transcription_service.domain import TranscriptCreatedEvent


class AnalysisResult(BaseModel):
    video_id: str
    word_count: int
    extra: dict = {}


class AnalysisBackend(ABC):

    @abstractmethod
    def analyze(self, transcript_text: str) -> AnalysisResult:
        """Analyze the given transcript text and return an AnalysisResult."""
        ...


def analyze_transcript(event: TranscriptCreatedEvent, backend: AnalysisBackend) -> AnalysisResult:
    """Analyze a transcript from a TranscriptCreatedEvent.

    Args:
        event: The TranscriptCreatedEvent containing the transcript path.
        backend: The analysis backend to use.

    Returns:
        The AnalysisResult from the backend.
    """
    transcript_path = Path(event.transcript_path)
    transcript_text = transcript_path.read_text(encoding="utf-8")
    result = backend.analyze(transcript_text)
    return result