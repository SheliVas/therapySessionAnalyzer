import pytest
import mongomock

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
