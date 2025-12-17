import os
import pytest
from unittest.mock import MagicMock
from src.transcription_service.run_worker import create_production_app
from src.transcription_service.backend import AssemblyAITranscriptionBackend
from src.transcription_service.rabbitmq_consumer import RabbitMQAudioExtractedConsumer

@pytest.fixture
def env_vars(mocker):
    mocker.patch.dict(os.environ, {
        "MINIO_ENDPOINT": "localhost:9000",
        "MINIO_ACCESS_KEY": "minio",
        "MINIO_SECRET_KEY": "minio123",
        "MONGO_URI": "mongodb://localhost:27017",
        "MONGO_DB": "therapy",
        "RABBITMQ_HOST": "localhost",
        "RABBITMQ_PORT": "5672",
        "RABBITMQ_USER": "guest",
        "RABBITMQ_PASS": "guest",
        "ASSEMBLYAI_API_KEY": "test_api_key"
    })

@pytest.mark.unit
def test_should_wire_assemblyai_backend_when_api_key_is_present(env_vars, mocker):
    mocker.patch("src.shared.minio_storage.MinioStorage")
    mocker.patch("src.shared.videos_repository.MongoVideosRepository")
    mocker.patch("src.transcription_service.rabbitmq_publisher.RabbitMQTranscriptEventPublisher")
    mock_consumer_class = mocker.patch("src.transcription_service.run_worker.RabbitMQAudioExtractedConsumer")
    mocker.patch("src.transcription_service.run_worker.MongoClient")
    mock_load_config = mocker.patch("src.transcription_service.run_worker.load_config")
    
    mock_config = MagicMock()
    mock_config.assemblyai_api_key = "test_api_key"
    mock_config.assemblyai_base_url = "https://api.test.com"
    mock_load_config.return_value = mock_config

    app = create_production_app()

    assert mock_load_config.called
    assert mock_consumer_class.called
    args, kwargs = mock_consumer_class.call_args
    
    assert isinstance(kwargs["backend"], AssemblyAITranscriptionBackend)
    assert kwargs["backend"].api_key == "test_api_key"

@pytest.mark.unit
def test_should_raise_error_when_api_key_is_missing(mocker):
    mocker.patch.dict(os.environ, {
        "MINIO_ENDPOINT": "localhost:9000",
        "MINIO_ACCESS_KEY": "minio",
        "MINIO_SECRET_KEY": "minio123",
        "MONGO_URI": "mongodb://localhost:27017",
        "MONGO_DB": "therapy",
        "RABBITMQ_HOST": "localhost",
        "RABBITMQ_PORT": "5672",
        "RABBITMQ_USER": "guest",
        "RABBITMQ_PASS": "guest",
    })
    if "ASSEMBLYAI_API_KEY" in os.environ:
        del os.environ["ASSEMBLYAI_API_KEY"]

    mocker.patch("src.shared.minio_storage.MinioStorage")
    mocker.patch("src.shared.videos_repository.MongoVideosRepository")
    mocker.patch("src.transcription_service.rabbitmq_publisher.RabbitMQTranscriptEventPublisher")
    mocker.patch("src.transcription_service.run_worker.RabbitMQAudioExtractedConsumer")
    mocker.patch("src.transcription_service.run_worker.MongoClient")

    with pytest.raises(KeyError) as excinfo:
        create_production_app()
    
    assert "ASSEMBLYAI_API_KEY" in str(excinfo.value)
