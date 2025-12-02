from abc import ABC, abstractmethod
from pathlib import Path

from pydantic import BaseModel

from src.audio_extractor_service.domain import AudioExtractedEvent


class TranscriptCreatedEvent(BaseModel):
    video_id: str
    transcript_path: str


class TranscriptionBackend(ABC):
    @abstractmethod
    def transcribe(self, audio_path: Path) -> str:
        """Transcribe audio at the given path and return the transcript text."""
        ...


def generate_transcript(
    event: AudioExtractedEvent,
    backend: TranscriptionBackend,
    base_output_dir: Path,
) -> TranscriptCreatedEvent:
    """
    Generate a transcript from an audio file.

    Args:
        event: The AudioExtractedEvent containing the audio path.
        backend: The transcription backend to use.
        base_output_dir: The base directory to write transcripts to.

    Returns:
        A TranscriptCreatedEvent with the path to the transcript file.
    """
    audio_path = Path(event.audio_path)
    transcript_text = backend.transcribe(audio_path)

    output_dir = base_output_dir / event.video_id
    output_dir.mkdir(parents=True, exist_ok=True)

    transcript_path = output_dir / "transcript.txt"
    transcript_path.write_text(transcript_text)

    return TranscriptCreatedEvent(
        video_id=event.video_id,
        transcript_path=str(transcript_path),
    )
