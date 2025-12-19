import pytest
import mongomock
from typing import Optional

from src.upload_service.domain import VideoEventPublisher, VideoUploadedEvent
from tests.fakes import FakeVideoEventPublisher, FakeStorageClient, FakeVideosRepository

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
