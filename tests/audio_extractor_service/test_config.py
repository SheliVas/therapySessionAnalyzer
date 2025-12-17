import os
import pytest
from unittest.mock import patch, MagicMock
from src.audio_extractor_service.run_worker import create_production_app

@pytest.mark.unit
def test_should_use_correct_env_vars_in_audio_extractor_production_app(mocker):
    mocker.patch.dict(os.environ, {
        "RABBITMQ_HOST": "rabbit",
        "RABBITMQ_PORT": "5672",
        "RABBITMQ_USER": "user",
        "RABBITMQ_PASS": "pass",
        "MINIO_ENDPOINT": "minio:9000",
        "MINIO_ACCESS_KEY": "minio-access",
        "MINIO_SECRET_KEY": "minio-secret",
        "MONGO_URI": "mongodb://mongo:27017",
        "MONGO_DB": "audio-db"
    })
    
    # Mock dependencies to avoid actual connections
    mocker.patch("src.audio_extractor_service.run_worker.MongoClient")
    mocker.patch("src.audio_extractor_service.run_worker.MinioStorage")
    mocker.patch("src.audio_extractor_service.run_worker.RabbitMQAudioEventPublisher")
    mocker.patch("src.audio_extractor_service.run_worker.RabbitMQVideoUploadedConsumer")
    mocker.patch("src.audio_extractor_service.run_worker.MongoVideosRepository")
    
    app = create_production_app()
    
    from src.audio_extractor_service.run_worker import MongoVideosRepository
    MongoVideosRepository.assert_called_once()
    args, kwargs = MongoVideosRepository.call_args
    assert args[1] == "audio-db"
