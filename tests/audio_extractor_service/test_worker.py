"""Tests for worker process: handle_audio_extraction_event."""
import pytest
from datetime import datetime

from src.upload_service.domain import VideoUploadedEvent
from src.audio_extractor_service.domain import (
    AudioExtractedEvent,
    handle_audio_extraction_event,
)


# --- Helpers ---

def _create_video_uploaded_event(video_id: str) -> VideoUploadedEvent:
    """Helper to create a VideoUploadedEvent."""
    return VideoUploadedEvent(
        video_id=video_id,
        filename="test.mp4",
        bucket="therapy-videos",
        key=f"videos/{video_id}/test.mp4",
        uploaded_at=datetime.now(),
    )


# --- Unit Tests: Happy Path ---

@pytest.mark.unit
def test_should_call_storage_client_download(
    fake_storage_client,
    fake_audio_converter,
    fake_audio_publisher,
    configured_storage_and_converter,
    video_id: str,
):
    """Worker should download video from storage using bucket/key from event."""
    event = _create_video_uploaded_event(video_id)
    
    handle_audio_extraction_event(
        event=event,
        storage_client=fake_storage_client,
        audio_converter=fake_audio_converter,
        publisher=fake_audio_publisher,
    )
    
    assert fake_storage_client.download_called_with is not None
    assert fake_storage_client.download_called_with["bucket"] == "therapy-videos"
    assert fake_storage_client.download_called_with["key"] == f"videos/{video_id}/test.mp4"


@pytest.mark.unit
def test_should_call_audio_converter(
    fake_storage_client,
    fake_audio_converter,
    fake_audio_publisher,
    video_id: str,
    video_bytes: bytes,
    audio_bytes: bytes,
):
    """Worker should convert downloaded video bytes to audio."""
    event = _create_video_uploaded_event(video_id)
    fake_storage_client.set_download_response(video_bytes)
    fake_audio_converter.set_convert_response(audio_bytes)
    
    handle_audio_extraction_event(
        event=event,
        storage_client=fake_storage_client,
        audio_converter=fake_audio_converter,
        publisher=fake_audio_publisher,
    )
    
    assert fake_audio_converter.convert_called_with == video_bytes


@pytest.mark.unit
def test_should_publish_exactly_one_event(
    fake_storage_client,
    fake_audio_converter,
    fake_audio_publisher,
    configured_storage_and_converter,
    video_id: str,
):
    """Worker should publish exactly one audio extracted event."""
    event = _create_video_uploaded_event(video_id)
    
    handle_audio_extraction_event(
        event=event,
        storage_client=fake_storage_client,
        audio_converter=fake_audio_converter,
        publisher=fake_audio_publisher,
    )
    
    assert len(fake_audio_publisher.published_events) == 1


@pytest.mark.unit
@pytest.mark.parametrize("field,expected_value", [
    ("video_id", "test-video-id"),  # Will be replaced by video_id fixture
    ("bucket", "therapy-audio"),
])
def test_published_event_should_have_correct_fields(
    fake_storage_client,
    fake_audio_converter,
    fake_audio_publisher,
    configured_storage_and_converter,
    video_id: str,
    field: str,
    expected_value: str,
):
    """Published event should have correct field values."""
    event = _create_video_uploaded_event(video_id)
    
    handle_audio_extraction_event(
        event=event,
        storage_client=fake_storage_client,
        audio_converter=fake_audio_converter,
        publisher=fake_audio_publisher,
    )
    
    published_event = fake_audio_publisher.published_events[0]
    assert isinstance(published_event, AudioExtractedEvent)
    
    if field == "video_id":
        assert getattr(published_event, field) == video_id
    else:
        assert getattr(published_event, field) == expected_value


@pytest.mark.unit
def test_published_event_should_have_correct_key_format(
    fake_storage_client,
    fake_audio_converter,
    fake_audio_publisher,
    configured_storage_and_converter,
    video_id: str,
):
    """Published event key should be audio/{video_id}/audio.mp3."""
    event = _create_video_uploaded_event(video_id)
    
    handle_audio_extraction_event(
        event=event,
        storage_client=fake_storage_client,
        audio_converter=fake_audio_converter,
        publisher=fake_audio_publisher,
    )
    
    published_event = fake_audio_publisher.published_events[0]
    assert published_event.key == f"audio/{video_id}/audio.mp3"


# --- Unit Tests: Error Cases ---

@pytest.mark.unit
@pytest.mark.parametrize("error_type,error_setup", [
    ("ValueError", lambda fsc, fac: fsc.set_download_response(b"")),
    ("converter_error", lambda fsc, fac: None),  # Will be set via mocker in test
    ("upload_error", lambda fsc, fac: None),     # Will be set via mocker in test
])
def test_should_not_publish_on_errors(
    fake_storage_client,
    fake_audio_converter,
    fake_audio_publisher,
    video_id: str,
    video_bytes: bytes,
    audio_bytes: bytes,
    error_type: str,
    error_setup,
    mocker,
):
    """Worker should not publish if any stage fails."""
    event = _create_video_uploaded_event(video_id)
    
    if error_type == "ValueError":
        error_setup(fake_storage_client, fake_audio_converter)
    elif error_type == "converter_error":
        fake_storage_client.set_download_response(video_bytes)
        mocker.patch.object(
            fake_audio_converter,
            'convert',
            side_effect=Exception("Conversion failed"),
        )
    elif error_type == "upload_error":
        fake_storage_client.set_download_response(video_bytes)
        fake_audio_converter.set_convert_response(audio_bytes)
        mocker.patch.object(
            fake_storage_client,
            'upload_file',
            side_effect=Exception("Upload failed"),
        )
    
    try:
        handle_audio_extraction_event(
            event=event,
            storage_client=fake_storage_client,
            audio_converter=fake_audio_converter,
            publisher=fake_audio_publisher,
        )
    except Exception:
        pass
    
    assert len(fake_audio_publisher.published_events) == 0


@pytest.mark.unit
def test_should_handle_download_failure_before_publishing(
    fake_storage_client,
    fake_audio_converter,
    fake_audio_publisher,
    video_id: str,
    mocker,
):
    """Worker should stop pipeline if download fails, without publishing."""
    event = _create_video_uploaded_event(video_id)
    
    mocker.patch.object(
        fake_storage_client,
        'download_file',
        side_effect=IOError("Download failed"),
    )
    
    try:
        handle_audio_extraction_event(
            event=event,
            storage_client=fake_storage_client,
            audio_converter=fake_audio_converter,
            publisher=fake_audio_publisher,
        )
    except IOError:
        pass
    
    assert len(fake_audio_publisher.published_events) == 0
    assert fake_audio_converter.convert_called_with is None
    assert fake_storage_client.upload_called_with is None


@pytest.mark.unit
def test_should_not_publish_multiple_times_on_success(
    fake_storage_client,
    fake_audio_converter,
    fake_audio_publisher,
    configured_storage_and_converter,
    video_id: str,
):
    """Worker should publish exactly once per call, not duplicate events."""
    event = _create_video_uploaded_event(video_id)
    
    handle_audio_extraction_event(
        event=event,
        storage_client=fake_storage_client,
        audio_converter=fake_audio_converter,
        publisher=fake_audio_publisher,
    )
    
    assert len(fake_audio_publisher.published_events) == 1
    
    handle_audio_extraction_event(
        event=event,
        storage_client=fake_storage_client,
        audio_converter=fake_audio_converter,
        publisher=fake_audio_publisher,
    )
    
    assert len(fake_audio_publisher.published_events) == 2


