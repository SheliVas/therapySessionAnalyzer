"""Tests for domain logic: extract_audio_from_video_event with MinIO storage and Repository updates."""
import pytest
from datetime import datetime

from src.upload_service.domain import VideoUploadedEvent
from src.audio_extractor_service.domain import (
    AudioExtractedEvent,
    extract_audio_from_video_event,
    handle_audio_extraction_event,
)
from tests.fakes import FakeVideosRepository


# --- Helpers ---

def _create_video_uploaded_event(
    video_id: str,
    bucket: str = "therapy-videos",
    key: str = None,
) -> VideoUploadedEvent:
    """Helper to create a VideoUploadedEvent."""
    if key is None:
        key = f"videos/{video_id}/test.mp4"
    return VideoUploadedEvent(
        video_id=video_id,
        filename="test.mp4",
        bucket=bucket,
        key=key,
        uploaded_at=datetime.now(),
    )


# --- Fixtures ---

@pytest.fixture
def fake_videos_repository() -> FakeVideosRepository:
    """Fixture for FakeVideosRepository."""
    return FakeVideosRepository()


# --- Fixtures: Execution Results ---

@pytest.fixture
def successful_extraction(
    configured_storage_and_converter,
    fake_videos_repository,
    video_id,
):
    """Execute the domain function successfully and return the result and collaborators."""
    fake_storage_client, fake_audio_converter = configured_storage_and_converter
    event = _create_video_uploaded_event(video_id)
    
    result = extract_audio_from_video_event(
        event=event,
        storage_client=fake_storage_client,
        audio_converter=fake_audio_converter,
        repository=fake_videos_repository,
    )
    
    return result, fake_storage_client, fake_audio_converter, fake_videos_repository


# --- Unit Tests: Happy Path ---

@pytest.mark.unit
def test_should_perform_successful_extraction_flow(
    successful_extraction,
    video_id,
    video_bytes,
    audio_bytes,
):
    """Verify the complete happy path flow: download -> convert -> upload -> update repo -> return event."""
    result, fake_storage_client, fake_audio_converter, fake_videos_repository = successful_extraction
    
    # 1. Download
    assert fake_storage_client.download_called_with == {
        "bucket": "therapy-videos",
        "key": f"videos/{video_id}/test.mp4",
    }
    
    # 2. Convert
    assert fake_audio_converter.convert_called_with == video_bytes
    
    # 3. Upload
    assert fake_storage_client.upload_called_with == {
        "bucket": "therapy-audio",
        "key": f"audio/{video_id}/audio.mp3",
        "content": audio_bytes,
    }
    
    # 4. Repository Update
    assert len(fake_videos_repository.mark_audio_extracted_calls) == 1
    call = fake_videos_repository.mark_audio_extracted_calls[0]
    assert call["video_id"] == video_id
    assert call["audio_path"] == f"therapy-audio/audio/{video_id}/audio.mp3"
    
    # 5. Return Event
    assert isinstance(result, AudioExtractedEvent)
    assert result.video_id == video_id
    assert result.bucket == "therapy-audio"
    assert result.key == f"audio/{video_id}/audio.mp3"


# --- Unit Tests: Error Cases ---

@pytest.mark.unit
@pytest.mark.parametrize("setup_func, expected_error_match", [
    (lambda fsc, fac, fvr: fsc.set_download_response(b""), "empty"),
    (lambda fsc, fac, fvr: setattr(fvr, 'should_raise_error', True), "Repository error"),
])
def test_should_raise_error_on_failure_conditions(
    configured_storage_and_converter,
    fake_videos_repository,
    video_id,
    setup_func,
    expected_error_match,
):
    """Domain should raise appropriate errors when dependencies fail or return invalid data."""
    fake_storage_client, fake_audio_converter = configured_storage_and_converter
    event = _create_video_uploaded_event(video_id)
    
    setup_func(fake_storage_client, fake_audio_converter, fake_videos_repository)
    
    with pytest.raises(ValueError, match=expected_error_match):
        extract_audio_from_video_event(
            event=event,
            storage_client=fake_storage_client,
            audio_converter=fake_audio_converter,
            repository=fake_videos_repository,
        )


@pytest.mark.unit
def test_should_not_call_repository_on_upstream_failure(
    fake_storage_client,
    fake_audio_converter,
    fake_videos_repository,
    video_id,
):
    """Domain should not call repository if extraction fails (e.g. empty download)."""
    event = _create_video_uploaded_event(video_id)
    fake_storage_client.set_download_response(b"")
    
    try:
        extract_audio_from_video_event(
            event=event,
            storage_client=fake_storage_client,
            audio_converter=fake_audio_converter,
            repository=fake_videos_repository,
        )
    except ValueError:
        pass
    
    assert len(fake_videos_repository.mark_audio_extracted_calls) == 0


# --- Unit Tests: Edge Cases ---

@pytest.mark.unit
@pytest.mark.parametrize("video_size_mb", [1, 10, 100])
def test_should_handle_various_video_sizes(
    fake_storage_client,
    fake_audio_converter,
    fake_videos_repository,
    video_id: str,
    audio_bytes: bytes,
    video_size_mb: int,
):
    """Domain should handle video files of various sizes."""
    event = _create_video_uploaded_event(video_id)
    large_video_bytes = b"x" * (video_size_mb * 1024 * 1024)
    fake_storage_client.set_download_response(large_video_bytes)
    fake_audio_converter.set_convert_response(audio_bytes)
    
    result = extract_audio_from_video_event(
        event=event,
        storage_client=fake_storage_client,
        audio_converter=fake_audio_converter,
        repository=fake_videos_repository,
    )
    
    assert result.video_id == video_id
    assert fake_audio_converter.convert_called_with == large_video_bytes


@pytest.mark.unit
@pytest.mark.parametrize("custom_bucket,custom_key", [
    ("my-custom-videos", "uploads/video.mp4"),
    ("archive-bucket", "old-videos/2023/video.mp4"),
])
def test_should_respect_different_source_buckets(
    fake_storage_client,
    fake_audio_converter,
    fake_videos_repository,
    video_id: str,
    video_bytes: bytes,
    audio_bytes: bytes,
    custom_bucket: str,
    custom_key: str,
):
    """Domain should respect bucket and key from event, not hardcode them."""
    event = _create_video_uploaded_event(
        video_id,
        bucket=custom_bucket,
        key=custom_key,
    )
    fake_storage_client.set_download_response(video_bytes)
    fake_audio_converter.set_convert_response(audio_bytes)
    
    extract_audio_from_video_event(
        event=event,
        storage_client=fake_storage_client,
        audio_converter=fake_audio_converter,
        repository=fake_videos_repository,
    )
    
    assert fake_storage_client.download_called_with["bucket"] == custom_bucket
    assert fake_storage_client.download_called_with["key"] == custom_key


# --- Integration: Handler ---

@pytest.mark.unit
def test_handler_should_call_domain_function_with_repository(
    fake_storage_client,
    fake_audio_converter,
    fake_audio_publisher,
    fake_videos_repository,
    video_id: str,
    video_bytes: bytes,
    audio_bytes: bytes,
):
    """Handler should pass repository to domain function and publish on success."""
    event = _create_video_uploaded_event(video_id)
    fake_storage_client.set_download_response(video_bytes)
    fake_audio_converter.set_convert_response(audio_bytes)
    
    handle_audio_extraction_event(
        event=event,
        storage_client=fake_storage_client,
        audio_converter=fake_audio_converter,
        repository=fake_videos_repository,
        publisher=fake_audio_publisher,
    )
    
    assert len(fake_videos_repository.mark_audio_extracted_calls) == 1
    assert len(fake_audio_publisher.published_events) == 1


@pytest.mark.unit
def test_should_call_repository_mark_audio_extracted_with_correct_path(
    fake_storage_client,
    fake_audio_converter,
    fake_videos_repository,
    video_id: str,
    video_bytes: bytes,
    audio_bytes: bytes,
):
    """extract_audio_from_video_event should call repository with correct audio_path."""
    event = _create_video_uploaded_event(video_id)
    fake_storage_client.set_download_response(video_bytes)
    fake_audio_converter.set_convert_response(audio_bytes)
    
    extract_audio_from_video_event(
        event=event,
        storage_client=fake_storage_client,
        audio_converter=fake_audio_converter,
        repository=fake_videos_repository,
    )
    
    assert len(fake_videos_repository.mark_audio_extracted_calls) == 1
    call = fake_videos_repository.mark_audio_extracted_calls[0]
    assert call["video_id"] == video_id
    assert "therapy-audio" in call["audio_path"]
    assert "audio.mp3" in call["audio_path"]


@pytest.mark.unit
def test_should_not_publish_on_repository_failure(
    fake_storage_client,
    fake_audio_converter,
    fake_audio_publisher,
    fake_videos_repository,
    video_id: str,
    video_bytes: bytes,
    audio_bytes: bytes,
):
    """Handler should not publish if repository.mark_audio_extracted fails."""
    event = _create_video_uploaded_event(video_id)
    fake_storage_client.set_download_response(video_bytes)
    fake_audio_converter.set_convert_response(audio_bytes)
    fake_videos_repository.should_raise_error = True
    
    with pytest.raises(ValueError, match="Repository error"):
        handle_audio_extraction_event(
            event=event,
            storage_client=fake_storage_client,
            audio_converter=fake_audio_converter,
            repository=fake_videos_repository,
            publisher=fake_audio_publisher,
        )
    
    assert len(fake_audio_publisher.published_events) == 0
