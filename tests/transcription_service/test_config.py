import os
import pytest
from unittest.mock import patch, MagicMock
from src.transcription_service.run_worker import create_production_app

@pytest.mark.unit
def test_should_use_correct_env_vars_in_transcription_production_app(mocker):
    mocker.patch.dict(os.environ, {
        "RABBITMQ_HOST": "rabbit",
        "RABBITMQ_PORT": "5672",
        "RABBITMQ_USER": "user",
        "RABBITMQ_PASS": "pass",
        "MINIO_ENDPOINT": "minio:9000",
        "MINIO_ACCESS_KEY": "minio-access",
        "MINIO_SECRET_KEY": "minio-secret",
        "MONGO_URI": "mongodb://mongo:27017",
        "MONGO_DB": "trans-db"
    })
    
    # Mock dependencies to avoid actual connections
    mocker.patch("src.transcription_service.run_worker.MongoClient")
    mocker.patch("src.transcription_service.run_worker.MinioStorage")
    mocker.patch("src.transcription_service.run_worker.RabbitMQTranscriptEventPublisher")
    mocker.patch("src.transcription_service.run_worker.RabbitMQAudioExtractedConsumer")
    mocker.patch("src.transcription_service.run_worker.MongoVideosRepository")
    
    app = create_production_app()
    
    from src.transcription_service.run_worker import MongoVideosRepository
    MongoVideosRepository.assert_called_once()
    args, kwargs = MongoVideosRepository.call_args
    assert args[1] == "trans-db"
