import pytest
import mongomock
from typing import Optional

from src.upload_service.domain import VideoEventPublisher, VideoUploadedEvent


class FakeVideoEventPublisher(VideoEventPublisher):
    """Global fake publisher for upload service tests."""
    def __init__(self) -> None:
        self.published: list[VideoUploadedEvent] = []

    def publish_video_uploaded(self, event: VideoUploadedEvent) -> None:
        self.published.append(event)


class FakeStorageClient:
    """Shared fake StorageClient that records download/upload calls."""
    def __init__(self) -> None:
        self.download_response: Optional[bytes] = None
        self.download_called_with: Optional[dict] = None
        self.upload_called_with: Optional[dict] = None
    
    def set_download_response(self, content: bytes) -> None:
        """Set the response for download_file calls."""
        self.download_response = content
    
    def download_file(self, bucket: str, key: str) -> bytes:
        """Record the call and return the set response."""
        self.download_called_with = {"bucket": bucket, "key": key}
        return self.download_response or b""
    
    def upload_file(self, bucket: str, key: str, content: bytes) -> None:
        """Record the upload call."""
        self.upload_called_with = {"bucket": bucket, "key": key, "content": content}


class FakeVideosRepository:
    """Unified fake repository for testing video status updates."""
    def __init__(self) -> None:
        self.mark_audio_extracted_calls: list[dict] = []
        self.mark_transcribed_calls: list[dict] = []
        self.should_raise_error = False
    
    def mark_audio_extracted(self, video_id: str, audio_path: str) -> None:
        """Record mark_audio_extracted call."""
        self.mark_audio_extracted_calls.append({
            "video_id": video_id,
            "audio_path": audio_path,
        })
        if self.should_raise_error:
            raise ValueError("Repository error")
    
    def mark_transcribed(self, video_id: str, transcript_path: str) -> None:
        """Record mark_transcribed call."""
        self.mark_transcribed_calls.append({
            "video_id": video_id,
            "transcript_path": transcript_path,
        })
        if self.should_raise_error:
            raise ValueError("Repository error")


@pytest.fixture
def fake_video_publisher() -> FakeVideoEventPublisher:
    """Global fixture for FakeVideoEventPublisher."""
    return FakeVideoEventPublisher()


@pytest.fixture
def fake_storage_client() -> FakeStorageClient:
    """Global fixture for FakeStorageClient."""
    return FakeStorageClient()


@pytest.fixture
def fake_videos_repository() -> FakeVideosRepository:
    """Global fixture for FakeVideosRepository."""
    return FakeVideosRepository()


@pytest.fixture
def mongo_client():
    """Global fixture for mocking MongoDB."""
    return mongomock.MongoClient()


@pytest.fixture
def mock_channel(mocker):
    return mocker.MagicMock()


@pytest.fixture
def mock_connection(mocker, mock_channel):
    connection = mocker.MagicMock()
    connection.channel.return_value = mock_channel
    return connection


@pytest.fixture
def mock_pika(mocker, mock_connection):
    pika_mock = mocker.MagicMock()
    pika_mock.BlockingConnection.return_value = mock_connection
    return pika_mock
