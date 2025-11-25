from pathlib import Path

from src.upload_service.events import VideoUploadedEvent
from src.audio_extractor_service.domain import (
    AudioExtractedEvent,
    handle_video_uploaded,
)


def test_should_write_audio_file_and_return_event_when_video_uploaded(tmp_path):
    some_video_bytes = b"fake-video-content"
    some_video_id = "video-123"
    some_filename = "video.mp4"

    video_path = tmp_path / some_filename
    video_path.write_bytes(some_video_bytes)
    base_output_dir = tmp_path / "data" / "audio"

    event = VideoUploadedEvent(
        video_id=some_video_id,
        filename=some_filename,
        storage_path=str(video_path),
    )

    result: AudioExtractedEvent = handle_video_uploaded(
        event=event,
        base_output_dir=base_output_dir,
    )

    assert isinstance(result, AudioExtractedEvent), f"expected AudioExtractedEvent, got {type(result)}"
    assert result.video_id == some_video_id, f"expected video_id {some_video_id}, got {result.video_id}"

    audio_path = Path(result.audio_path)
    expected_audio_path = base_output_dir / some_video_id / "audio.mp3"

    assert audio_path == expected_audio_path, f"expected audio_path {expected_audio_path}, got {audio_path}"

    assert audio_path.is_file(), f"expected audio file at {audio_path}, but it does not exist"

    written_bytes = audio_path.read_bytes()
    assert written_bytes == some_video_bytes, (
        f"expected audio bytes {some_video_bytes!r}, got {written_bytes!r}"
    )