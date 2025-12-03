from pathlib import Path

from src.upload_service.domain import VideoUploadedEvent
from src.audio_extractor_service.domain import AudioExtractedEvent
from src.audio_extractor_service.worker import process_video_uploaded_event
from tests.audio_extractor_service.conftest import FakeAudioEventPublisher



def test_should_return_audio_extracted_event_and_write_audio_file(
    event: VideoUploadedEvent,
    base_output_dir: Path,
    fake_publisher: FakeAudioEventPublisher,
    video_id: str,
    video_bytes: bytes,
):
    result = process_video_uploaded_event(
        event=event,
        base_output_dir=base_output_dir,
        publisher=fake_publisher,
    )

    assert isinstance(result, AudioExtractedEvent)
    assert result.video_id == video_id

    audio_path = Path(result.audio_path)
    expected_audio_path = base_output_dir / video_id / "audio.mp3"
    assert audio_path == expected_audio_path
    assert audio_path.is_file()

    written_bytes = audio_path.read_bytes()
    assert written_bytes == video_bytes


def test_should_publish_audio_extracted_event_via_publisher(
    event: VideoUploadedEvent,
    base_output_dir: Path,
    fake_publisher: FakeAudioEventPublisher,
):
    result = process_video_uploaded_event(
        event=event,
        base_output_dir=base_output_dir,
        publisher=fake_publisher,
    )

    assert len(fake_publisher.published_events) == 1

    published_event = fake_publisher.published_events[0]
    assert published_event.video_id == result.video_id
    assert published_event.audio_path == result.audio_path
