import pytest
import mongomock
from unittest.mock import MagicMock

@pytest.fixture
def mongo_client():
    """Global fixture for mocking MongoDB."""
    return mongomock.MongoClient()


@pytest.fixture
def mock_channel():
    channel = MagicMock()
    return channel


@pytest.fixture
def mock_connection(mock_channel):
    connection = MagicMock()
    connection.channel.return_value = mock_channel
    return connection


@pytest.fixture
def mock_pika(mock_connection):
    pika_mock = MagicMock()
    pika_mock.BlockingConnection.return_value = mock_connection
    return pika_mock
