from pathlib import Path

from pydantic import BaseModel

from src.upload_service.events import VideoUploadedEvent  # adjust import if needed


class AudioExtractedEvent(BaseModel):
    video_id: str
    audio_path: str


def handle_video_uploaded(
    event: VideoUploadedEvent,
    base_output_dir: Path,
) -> AudioExtractedEvent:
    video_path = Path(event.storage_path)

    output_dir = base_output_dir / event.video_id
    output_dir.mkdir(parents=True, exist_ok=True)

    audio_path = output_dir / "audio.mp3"

    content = video_path.read_bytes()
    audio_path.write_bytes(content)

    return AudioExtractedEvent(
        video_id=event.video_id,
        audio_path=str(audio_path),
    )
