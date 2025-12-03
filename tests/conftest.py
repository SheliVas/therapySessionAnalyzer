import pytest
import mongomock

from src.upload_service.domain import VideoEventPublisher, VideoUploadedEvent


class FakeVideoEventPublisher(VideoEventPublisher):
    """Global fake publisher for upload service tests."""
    def __init__(self) -> None:
        self.published: list[VideoUploadedEvent] = []

    def publish_video_uploaded(self, event: VideoUploadedEvent) -> None:
        self.published.append(event)


@pytest.fixture
def fake_video_publisher() -> FakeVideoEventPublisher:
    """Global fixture for FakeVideoEventPublisher."""
    return FakeVideoEventPublisher()


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
