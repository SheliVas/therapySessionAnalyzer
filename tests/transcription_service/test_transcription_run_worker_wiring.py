import pytest
import os
from unittest.mock import MagicMock, patch, call

from src.transcription_service.run_worker import create_production_app
from src.shared.config import MinIOConfig, MongoConfig, AudioExtractedConsumerConfig, TranscriptCreatedPublisherConfig
from src.shared.minio_storage import MinioStorage
from src.shared.videos_repository import MongoVideosRepository


# --- Fixtures ---

@pytest.fixture
def env_vars(monkeypatch):
    """Set required environment variables for production app creation."""
    monkeypatch.setenv("RABBITMQ_HOST", "localhost")
    monkeypatch.setenv("RABBITMQ_PORT", "5672")
    monkeypatch.setenv("RABBITMQ_USER", "guest")
    monkeypatch.setenv("RABBITMQ_PASS", "guest")
    monkeypatch.setenv("AUDIO_EXTRACTED_QUEUE", "audio.extracted")
    monkeypatch.setenv("TRANSCRIPT_CREATED_QUEUE", "transcript.created")
    monkeypatch.setenv("MINIO_ENDPOINT", "localhost:9000")
    monkeypatch.setenv("MINIO_ACCESS_KEY", "minioadmin")
    monkeypatch.setenv("MINIO_SECRET_KEY", "minioadmin")
    monkeypatch.setenv("MONGO_URI", "mongodb://localhost:27017")
    monkeypatch.setenv("MONGO_DB", "therapy_analysis")
    monkeypatch.setenv("ASSEMBLYAI_API_KEY", "test-key")
    return {
        "RABBITMQ_HOST": "localhost",
        "RABBITMQ_PORT": "5672",
        "RABBITMQ_USER": "guest",
        "RABBITMQ_PASS": "guest",
        "AUDIO_EXTRACTED_QUEUE": "audio.extracted",
        "TRANSCRIPT_CREATED_QUEUE": "transcript.created",
        "MINIO_ENDPOINT": "localhost:9000",
        "MINIO_ACCESS_KEY": "minioadmin",
        "MINIO_SECRET_KEY": "minioadmin",
        "MONGO_URI": "mongodb://localhost:27017",
        "MONGO_DB": "therapy_analysis",
        "ASSEMBLYAI_API_KEY": "test-key",
    }


# --- Unit Tests ---

@pytest.mark.unit
def test_should_instantiate_minio_storage_with_config(env_vars, mocker):
    """Test that MinioStorage is instantiated with MinIOConfig from environment."""
    mock_minio_storage_class = mocker.patch("src.transcription_service.run_worker.MinioStorage")
    mock_mongo_client = mocker.MagicMock()
    mock_repo = mocker.MagicMock()
    mocker.patch("src.transcription_service.run_worker.MongoClient", return_value=mock_mongo_client)
    mocker.patch("src.transcription_service.run_worker.MongoVideosRepository", return_value=mock_repo)
    mocker.patch("src.transcription_service.run_worker.RabbitMQTranscriptEventPublisher")
    mocker.patch("src.transcription_service.run_worker.RabbitMQAudioExtractedConsumer")
    
    create_production_app()
    
    mock_minio_storage_class.assert_called_once()
    call_args = mock_minio_storage_class.call_args
    config = call_args[0][0]
    assert config.endpoint == "localhost:9000"
    assert config.access_key == "minioadmin"
    assert config.secret_key == "minioadmin"


@pytest.mark.unit
def test_should_instantiate_mongo_client_with_correct_uri(env_vars, mocker):
    """Test that MongoClient is instantiated with correct URI from environment."""
    mock_mongo_client_class = mocker.patch("src.transcription_service.run_worker.MongoClient")
    mocker.patch("src.transcription_service.run_worker.MinioStorage")
    mocker.patch("src.transcription_service.run_worker.MongoVideosRepository")
    mocker.patch("src.transcription_service.run_worker.RabbitMQTranscriptEventPublisher")
    mocker.patch("src.transcription_service.run_worker.RabbitMQAudioExtractedConsumer")
    
    create_production_app()
    
    mock_mongo_client_class.assert_called_once_with("mongodb://localhost:27017")


@pytest.mark.unit
def test_should_instantiate_mongo_videos_repository_with_client_and_db_name(env_vars, mocker):
    """Test that MongoVideosRepository is instantiated with MongoDB client and db name."""
    mock_mongo_client = mocker.MagicMock()
    mock_repo_class = mocker.patch("src.transcription_service.run_worker.MongoVideosRepository")
    mocker.patch("src.transcription_service.run_worker.MongoClient", return_value=mock_mongo_client)
    mocker.patch("src.transcription_service.run_worker.MinioStorage")
    mocker.patch("src.transcription_service.run_worker.RabbitMQTranscriptEventPublisher")
    mocker.patch("src.transcription_service.run_worker.RabbitMQAudioExtractedConsumer")
    
    create_production_app()
    
    mock_repo_class.assert_called_once_with(mock_mongo_client, "therapy_analysis")


@pytest.mark.unit
def test_should_instantiate_consumer_with_repository_argument(env_vars, mocker):
    """Test that RabbitMQAudioExtractedConsumer is instantiated with repository argument."""
    mock_storage = mocker.MagicMock()
    mock_repo = mocker.MagicMock()
    mock_publisher = mocker.MagicMock()
    mock_consumer_class = mocker.patch("src.transcription_service.run_worker.RabbitMQAudioExtractedConsumer")
    
    mocker.patch("src.transcription_service.run_worker.MinioStorage", return_value=mock_storage)
    mock_mongo_client = mocker.MagicMock()
    mocker.patch("src.transcription_service.run_worker.MongoClient", return_value=mock_mongo_client)
    mocker.patch("src.transcription_service.run_worker.MongoVideosRepository", return_value=mock_repo)
    mocker.patch("src.transcription_service.run_worker.RabbitMQTranscriptEventPublisher", return_value=mock_publisher)
    
    create_production_app()
    
    call_kwargs = mock_consumer_class.call_args[1]
    assert "repository" in call_kwargs
    assert call_kwargs["repository"] is mock_repo


@pytest.mark.unit
def test_should_return_dict_with_all_dependencies(env_vars, mocker):
    """Test that create_production_app returns a dict with storage, repository, publisher, and consumer."""

    mock_storage = mocker.MagicMock()
    mock_repo = mocker.MagicMock()
    mock_publisher = mocker.MagicMock()
    mock_consumer = mocker.MagicMock()
    
    mocker.patch("src.transcription_service.run_worker.MinioStorage", return_value=mock_storage)
    mock_mongo_client = mocker.MagicMock()
    mocker.patch("src.transcription_service.run_worker.MongoClient", return_value=mock_mongo_client)
    mocker.patch("src.transcription_service.run_worker.MongoVideosRepository", return_value=mock_repo)
    mocker.patch("src.transcription_service.run_worker.RabbitMQTranscriptEventPublisher", return_value=mock_publisher)
    mocker.patch("src.transcription_service.run_worker.RabbitMQAudioExtractedConsumer", return_value=mock_consumer)
    

    result = create_production_app()
    

    assert isinstance(result, dict)
    assert "storage_client" in result
    assert "repository" in result
    assert "publisher" in result
    assert "consumer" in result
    assert result["storage_client"] is mock_storage
    assert result["repository"] is mock_repo
    assert result["publisher"] is mock_publisher
    assert result["consumer"] is mock_consumer


@pytest.mark.unit
def test_should_pass_storage_client_to_consumer(env_vars, mocker):
    """Test that MinioStorage instance is passed to consumer as storage_client."""
    mock_storage = mocker.MagicMock()
    mock_repo = mocker.MagicMock()
    mock_publisher = mocker.MagicMock()
    mock_consumer_class = mocker.patch("src.transcription_service.run_worker.RabbitMQAudioExtractedConsumer")
    
    mocker.patch("src.transcription_service.run_worker.MinioStorage", return_value=mock_storage)
    mock_mongo_client = mocker.MagicMock()
    mocker.patch("src.transcription_service.run_worker.MongoClient", return_value=mock_mongo_client)
    mocker.patch("src.transcription_service.run_worker.MongoVideosRepository", return_value=mock_repo)
    mocker.patch("src.transcription_service.run_worker.RabbitMQTranscriptEventPublisher", return_value=mock_publisher)
    
    create_production_app()
    
    call_kwargs = mock_consumer_class.call_args[1]
    assert "storage_client" in call_kwargs
    assert call_kwargs["storage_client"] is mock_storage


@pytest.mark.unit
def test_should_pass_publisher_to_consumer(env_vars, mocker):
    """Test that RabbitMQTranscriptEventPublisher instance is passed to consumer as publisher."""
    mock_storage = mocker.MagicMock()
    mock_repo = mocker.MagicMock()
    mock_publisher = mocker.MagicMock()
    mock_consumer_class = mocker.patch("src.transcription_service.run_worker.RabbitMQAudioExtractedConsumer")
    
    mocker.patch("src.transcription_service.run_worker.MinioStorage", return_value=mock_storage)
    mock_mongo_client = mocker.MagicMock()
    mocker.patch("src.transcription_service.run_worker.MongoClient", return_value=mock_mongo_client)
    mocker.patch("src.transcription_service.run_worker.MongoVideosRepository", return_value=mock_repo)
    mocker.patch("src.transcription_service.run_worker.RabbitMQTranscriptEventPublisher", return_value=mock_publisher)
    
    create_production_app()
    
    call_kwargs = mock_consumer_class.call_args[1]
    assert "publisher" in call_kwargs
    assert call_kwargs["publisher"] is mock_publisher


@pytest.mark.unit
def test_should_build_consumer_config_from_environment(env_vars, mocker):
    """Test that RabbitMQAudioExtractedConsumer is called with config from environment."""
    mock_storage = mocker.MagicMock()
    mock_repo = mocker.MagicMock()
    mock_publisher = mocker.MagicMock()
    mock_consumer_class = mocker.patch("src.transcription_service.run_worker.RabbitMQAudioExtractedConsumer")
    
    mocker.patch("src.transcription_service.run_worker.MinioStorage", return_value=mock_storage)
    mock_mongo_client = mocker.MagicMock()
    mocker.patch("src.transcription_service.run_worker.MongoClient", return_value=mock_mongo_client)
    mocker.patch("src.transcription_service.run_worker.MongoVideosRepository", return_value=mock_repo)
    mocker.patch("src.transcription_service.run_worker.RabbitMQTranscriptEventPublisher", return_value=mock_publisher)
    
    create_production_app()
    
    call_kwargs = mock_consumer_class.call_args[1]
    assert "config" in call_kwargs
    config = call_kwargs["config"]
    assert config.host == "localhost"
    assert config.port == 5672
    assert config.username == "guest"
    assert config.password == "guest"
    assert config.queue_name == "audio.extracted"


@pytest.mark.unit
def test_should_build_publisher_config_from_environment(env_vars, mocker):
    """Test that RabbitMQTranscriptEventPublisher is called with correct config."""
    mock_storage = mocker.MagicMock()
    mock_repo = mocker.MagicMock()
    mock_publisher_class = mocker.patch("src.transcription_service.run_worker.RabbitMQTranscriptEventPublisher")
    mock_consumer = mocker.MagicMock()
    
    mocker.patch("src.transcription_service.run_worker.MinioStorage", return_value=mock_storage)
    mock_mongo_client = mocker.MagicMock()
    mocker.patch("src.transcription_service.run_worker.MongoClient", return_value=mock_mongo_client)
    mocker.patch("src.transcription_service.run_worker.MongoVideosRepository", return_value=mock_repo)
    mocker.patch("src.transcription_service.run_worker.RabbitMQAudioExtractedConsumer", return_value=mock_consumer)
    
    create_production_app()
    
    call_args = mock_publisher_class.call_args[0]
    config = call_args[0]
    assert config.host == "localhost"
    assert config.port == 5672
    assert config.username == "guest"
    assert config.password == "guest"
    assert config.queue_name == "transcript.created"
