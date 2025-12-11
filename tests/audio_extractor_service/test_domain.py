"""Tests for domain logic: extract_audio_from_video_event with MinIO storage."""
import pytest
from datetime import datetime

from src.upload_service.domain import VideoUploadedEvent
from src.audio_extractor_service.domain import (
    AudioExtractedEvent,
    extract_audio_from_video_event,
)


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


# --- Unit Tests: Happy Path ---

@pytest.mark.unit
def test_should_download_video_from_minio_bucket(
    fake_storage_client,
    fake_audio_converter,
    video_id: str,
    video_bytes: bytes,
    audio_bytes: bytes,
):
    """Domain should call storage_client.download_file with bucket/key from event."""
    event = _create_video_uploaded_event(video_id)
    fake_storage_client.set_download_response(video_bytes)
    fake_audio_converter.set_convert_response(audio_bytes)
    
    extract_audio_from_video_event(
        event=event,
        storage_client=fake_storage_client,
        audio_converter=fake_audio_converter,
    )
    
    assert fake_storage_client.download_called_with == {
        "bucket": "therapy-videos",
        "key": f"videos/{video_id}/test.mp4",
    }


@pytest.mark.unit
def test_should_convert_video_bytes_to_audio(
    fake_storage_client,
    fake_audio_converter,
    video_id: str,
    video_bytes: bytes,
    audio_bytes: bytes,
):
    """Domain should call audio_converter.convert with downloaded bytes."""
    event = _create_video_uploaded_event(video_id)
    fake_storage_client.set_download_response(video_bytes)
    fake_audio_converter.set_convert_response(audio_bytes)
    
    extract_audio_from_video_event(
        event=event,
        storage_client=fake_storage_client,
        audio_converter=fake_audio_converter,
    )
    
    assert fake_audio_converter.convert_called_with == video_bytes


@pytest.mark.unit
def test_should_upload_mp3_to_minio_therapy_audio_bucket(
    fake_storage_client,
    fake_audio_converter,
    video_id: str,
    video_bytes: bytes,
    audio_bytes: bytes,
):
    """Domain should upload MP3 to therapy-audio bucket with key audio/{video_id}/audio.mp3."""
    event = _create_video_uploaded_event(video_id)
    fake_storage_client.set_download_response(video_bytes)
    fake_audio_converter.set_convert_response(audio_bytes)
    
    extract_audio_from_video_event(
        event=event,
        storage_client=fake_storage_client,
        audio_converter=fake_audio_converter,
    )
    
    assert fake_storage_client.upload_called_with == {
        "bucket": "therapy-audio",
        "key": f"audio/{video_id}/audio.mp3",
        "content": audio_bytes,
    }


@pytest.mark.unit
def test_should_return_audio_extracted_event_with_bucket_and_key(
    fake_storage_client,
    fake_audio_converter,
    video_id: str,
    video_bytes: bytes,
    audio_bytes: bytes,
):
    """Domain should return AudioExtractedEvent with bucket/key metadata."""
    event = _create_video_uploaded_event(video_id)
    fake_storage_client.set_download_response(video_bytes)
    fake_audio_converter.set_convert_response(audio_bytes)
    
    result = extract_audio_from_video_event(
        event=event,
        storage_client=fake_storage_client,
        audio_converter=fake_audio_converter,
    )
    
    assert isinstance(result, AudioExtractedEvent)
    assert result.video_id == video_id
    assert result.bucket == "therapy-audio"
    assert result.key == f"audio/{video_id}/audio.mp3"


# --- Unit Tests: Error Cases ---

@pytest.mark.unit
def test_should_raise_value_error_when_storage_client_returns_empty_bytes(
    fake_storage_client,
    fake_audio_converter,
    video_id: str,
):
    """Domain should raise ValueError when download returns empty bytes."""
    event = _create_video_uploaded_event(video_id)
    fake_storage_client.set_download_response(b"")
    
    with pytest.raises(ValueError, match="empty"):
        extract_audio_from_video_event(
            event=event,
            storage_client=fake_storage_client,
            audio_converter=fake_audio_converter,
        )


@pytest.mark.unit
@pytest.mark.parametrize("should_call_converter,should_call_upload", [
    (False, False),  # Both should be skipped on empty bytes
])
def test_should_not_call_downstream_on_empty_download(
    fake_storage_client,
    fake_audio_converter,
    video_id: str,
    should_call_converter: bool,
    should_call_upload: bool,
):
    """Domain should not call converter or upload if download returns empty bytes."""
    event = _create_video_uploaded_event(video_id)
    fake_storage_client.set_download_response(b"")
    
    try:
        extract_audio_from_video_event(
            event=event,
            storage_client=fake_storage_client,
            audio_converter=fake_audio_converter,
        )
    except ValueError:
        pass
    
    if not should_call_converter:
        assert fake_audio_converter.convert_called_with is None
    if not should_call_upload:
        assert fake_storage_client.upload_called_with is None


# --- Unit Tests: Edge Cases ---

@pytest.mark.unit
@pytest.mark.parametrize("video_size_mb", [1, 10, 100])
def test_should_handle_various_video_sizes(
    fake_storage_client,
    fake_audio_converter,
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
    )
    
    assert result.video_id == video_id
    assert fake_audio_converter.convert_called_with == large_video_bytes


@pytest.mark.unit
def test_should_upload_exact_audio_bytes_from_converter(
    fake_storage_client,
    fake_audio_converter,
    video_id: str,
    video_bytes: bytes,
):
    """Domain should upload the exact bytes returned by converter."""
    event = _create_video_uploaded_event(video_id)
    unique_audio_bytes = b"unique-audio-signature-123"
    fake_storage_client.set_download_response(video_bytes)
    fake_audio_converter.set_convert_response(unique_audio_bytes)
    
    extract_audio_from_video_event(
        event=event,
        storage_client=fake_storage_client,
        audio_converter=fake_audio_converter,
    )
    
    assert fake_storage_client.upload_called_with["content"] == unique_audio_bytes


@pytest.mark.unit
@pytest.mark.parametrize("custom_bucket,custom_key", [
    ("my-custom-videos", "uploads/video.mp4"),
    ("archive-bucket", "old-videos/2023/video.mp4"),
])
def test_should_respect_different_source_buckets(
    fake_storage_client,
    fake_audio_converter,
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
    )
    
    assert fake_storage_client.download_called_with["bucket"] == custom_bucket
    assert fake_storage_client.download_called_with["key"] == custom_key


@pytest.mark.unit
@pytest.mark.parametrize("source_bucket", [
    "my-custom-videos",
    "archive-bucket",
    "temp-uploads",
])
def test_should_always_upload_to_therapy_audio_bucket(
    fake_storage_client,
    fake_audio_converter,
    video_id: str,
    video_bytes: bytes,
    audio_bytes: bytes,
    source_bucket: str,
):
    """Domain should always upload result to therapy-audio, regardless of source bucket."""
    event = _create_video_uploaded_event(video_id, bucket=source_bucket)
    fake_storage_client.set_download_response(video_bytes)
    fake_audio_converter.set_convert_response(audio_bytes)
    
    extract_audio_from_video_event(
        event=event,
        storage_client=fake_storage_client,
        audio_converter=fake_audio_converter,
    )
    
    assert fake_storage_client.upload_called_with["bucket"] == "therapy-audio"


@pytest.mark.unit
def test_should_preserve_video_id_in_output_key(
    fake_storage_client,
    fake_audio_converter,
    video_id: str,
    video_bytes: bytes,
    audio_bytes: bytes,
):
    """Domain should use video_id in output key, not filename."""
    event = _create_video_uploaded_event(
        video_id,
        key=f"videos/{video_id}/my-special-filename.mp4",
    )
    fake_storage_client.set_download_response(video_bytes)
    fake_audio_converter.set_convert_response(audio_bytes)
    
    extract_audio_from_video_event(
        event=event,
        storage_client=fake_storage_client,
        audio_converter=fake_audio_converter,
    )
    
    expected_key = f"audio/{video_id}/audio.mp3"
    assert fake_storage_client.upload_called_with["key"] == expected_key


