from pathlib import Path

from src.upload_service.events import VideoUploadedEvent
from src.audio_extractor_service.domain import AudioExtractedEvent
from src.audio_extractor_service.worker import (
    AudioEventPublisher,
    process_video_uploaded_event,
)


class FakeAudioEventPublisher:
    def __init__(self) -> None:
        self.published_events: list[AudioExtractedEvent] = []

    def publish_audio_extracted(self, event: AudioExtractedEvent) -> None:
        self.published_events.append(event)


def _create_fake_video(tmp_path: Path) -> tuple[VideoUploadedEvent, bytes, Path, Path]:
    video_bytes = b"fake-video-content"
    video_id = "some-video-id"
    filename = "some-video.mp4"

    video_path = tmp_path / filename
    video_path.write_bytes(video_bytes)

    base_output_dir = tmp_path / "data" / "audio_extractor_output"

    event = VideoUploadedEvent(
        video_id=video_id,
        filename=filename,
        storage_path=str(video_path),
    )

    return event, video_bytes, base_output_dir, video_path


def test_should_return_audio_extracted_event_and_write_audio_file(tmp_path: Path) -> None:
    event, video_bytes, base_output_dir, _ = _create_fake_video(tmp_path)
    publisher = FakeAudioEventPublisher()

    result: AudioExtractedEvent = process_video_uploaded_event(
        event=event,
        base_output_dir=base_output_dir,
        publisher=publisher,
    )

    assert isinstance(result, AudioExtractedEvent), f"expected AudioExtractedEvent, got {type(result)}"
    assert result.video_id == event.video_id, f"expected video_id {event.video_id}, got {result.video_id}"

    audio_path = Path(result.audio_path)
    expected_audio_path = base_output_dir / event.video_id / "audio.mp3"
    assert audio_path == expected_audio_path, f"expected audio_path {expected_audio_path}, got {audio_path}"
    assert audio_path.is_file(), f"expected audio file at {audio_path}, but it does not exist"

    written_bytes = audio_path.read_bytes()
    assert written_bytes == video_bytes, "expected audio file content to match video content"


def test_should_publish_audio_extracted_event_via_publisher(tmp_path: Path) -> None:
    event, _, base_output_dir, _ = _create_fake_video(tmp_path)
    publisher = FakeAudioEventPublisher()

    result = process_video_uploaded_event(
        event=event,
        base_output_dir=base_output_dir,
        publisher=publisher,
    )

    assert len(publisher.published_events) == 1, "expected one published event"

    published_event = publisher.published_events[0]
    assert published_event.video_id == result.video_id, f"expected video_id {result.video_id}, got {published_event.video_id}"
    assert published_event.audio_path == result.audio_path, f"expected audio_path {result.audio_path}, got {published_event.audio_path}"