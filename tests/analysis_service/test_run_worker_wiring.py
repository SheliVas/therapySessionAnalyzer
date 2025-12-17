"""Tests for run_worker.py factory and dependency wiring."""
import pytest

from src.analysis_service.run_worker import main


# --- Unit Tests ---

@pytest.mark.unit
def test_should_instantiate_minio_storage_from_config(mocker):
    """Verify main() instantiates MinioStorage with MINIO_* env vars."""
    # Mock all external dependencies
    mocker.patch("src.analysis_service.run_worker.load_config")
    mocker.patch("src.analysis_service.run_worker.MongoClient")
    mocker.patch("src.analysis_service.run_worker.MongoVideosRepository")
    mocker.patch("src.analysis_service.run_worker.MongoAnalysisRepository")
    mocker.patch("src.analysis_service.run_worker.SimpleWordCountBackend")
    mocker.patch("src.analysis_service.run_worker.RabbitMQAnalysisEventPublisher")
    mocker.patch("src.analysis_service.run_worker.RabbitMQTranscriptCreatedConsumer")
    mock_minio_storage = mocker.patch("src.analysis_service.run_worker.MinioStorage")

    try:
        main()
    except (AttributeError, TypeError):
        # Expected to fail since we're not fully mocking the consumer.run_forever()
        pass

    mock_minio_storage.assert_called_once()


@pytest.mark.unit
def test_should_instantiate_mongo_videos_repository_from_config(mocker):
    """Verify main() instantiates MongoVideosRepository with config."""
    # Mock all external dependencies
    config_mock = mocker.patch("src.analysis_service.run_worker.load_config")
    mongo_client_mock = mocker.patch("src.analysis_service.run_worker.MongoClient")
    mock_mongo_videos_repo = mocker.patch("src.analysis_service.run_worker.MongoVideosRepository")
    mocker.patch("src.analysis_service.run_worker.MongoAnalysisRepository")
    mocker.patch("src.analysis_service.run_worker.SimpleWordCountBackend")
    mocker.patch("src.analysis_service.run_worker.RabbitMQAnalysisEventPublisher")
    mocker.patch("src.analysis_service.run_worker.RabbitMQTranscriptCreatedConsumer")
    mocker.patch("src.analysis_service.run_worker.MinioStorage")

    config_instance = config_mock.return_value
    config_instance.mongo_db_name = "test_db"
    mongo_client_instance = mongo_client_mock.return_value

    try:
        main()
    except (AttributeError, TypeError):
        pass

    mock_mongo_videos_repo.assert_called_once_with(
        mongo_client_instance,
        db_name=config_instance.mongo_db_name,
    )


@pytest.mark.unit
def test_should_pass_storage_client_to_consumer(mocker):
    """Verify main() passes MinioStorage instance to RabbitMQTranscriptCreatedConsumer."""
    # Mock all external dependencies
    mocker.patch("src.analysis_service.run_worker.load_config")
    mocker.patch("src.analysis_service.run_worker.MongoClient")
    mocker.patch("src.analysis_service.run_worker.MongoVideosRepository")
    mocker.patch("src.analysis_service.run_worker.MongoAnalysisRepository")
    mocker.patch("src.analysis_service.run_worker.SimpleWordCountBackend")
    mocker.patch("src.analysis_service.run_worker.RabbitMQAnalysisEventPublisher")
    mock_consumer = mocker.patch("src.analysis_service.run_worker.RabbitMQTranscriptCreatedConsumer")
    mock_minio_storage = mocker.patch("src.analysis_service.run_worker.MinioStorage")

    mock_storage_instance = mock_minio_storage.return_value

    try:
        main()
    except (AttributeError, TypeError):
        pass

    # Verify consumer was called with storage_client kwarg
    call_kwargs = mock_consumer.call_args[1]
    assert call_kwargs["storage_client"] is mock_storage_instance


@pytest.mark.unit
def test_should_pass_videos_repository_to_consumer(mocker):
    """Verify main() passes MongoVideosRepository instance to RabbitMQTranscriptCreatedConsumer."""
    # Mock all external dependencies
    mocker.patch("src.analysis_service.run_worker.load_config")
    mocker.patch("src.analysis_service.run_worker.MongoClient")
    mock_mongo_videos_repo = mocker.patch("src.analysis_service.run_worker.MongoVideosRepository")
    mocker.patch("src.analysis_service.run_worker.MongoAnalysisRepository")
    mocker.patch("src.analysis_service.run_worker.SimpleWordCountBackend")
    mocker.patch("src.analysis_service.run_worker.RabbitMQAnalysisEventPublisher")
    mock_consumer = mocker.patch("src.analysis_service.run_worker.RabbitMQTranscriptCreatedConsumer")
    mocker.patch("src.analysis_service.run_worker.MinioStorage")

    mock_videos_repo_instance = mock_mongo_videos_repo.return_value

    try:
        main()
    except (AttributeError, TypeError):
        pass

    # Verify consumer was called with videos_repository kwarg
    call_kwargs = mock_consumer.call_args[1]
    assert call_kwargs["videos_repository"] is mock_videos_repo_instance


@pytest.mark.unit
def test_should_raise_when_minio_storage_initialization_fails(mocker):
    """Verify main() propagates MinioStorage initialization errors."""
    mocker.patch("src.analysis_service.run_worker.load_config")
    mocker.patch("src.analysis_service.run_worker.MongoClient")
    mocker.patch("src.analysis_service.run_worker.MongoVideosRepository")
    mocker.patch("src.analysis_service.run_worker.MongoAnalysisRepository")
    mocker.patch("src.analysis_service.run_worker.SimpleWordCountBackend")
    mocker.patch("src.analysis_service.run_worker.RabbitMQAnalysisEventPublisher")
    mocker.patch("src.analysis_service.run_worker.RabbitMQTranscriptCreatedConsumer")
    mock_minio_storage = mocker.patch("src.analysis_service.run_worker.MinioStorage")

    mock_minio_storage.side_effect = Exception("MinIO Connection Error")

    with pytest.raises(Exception, match="MinIO Connection Error"):
        main()


@pytest.mark.unit
def test_should_raise_when_mongo_videos_repository_initialization_fails(mocker):
    """Verify main() propagates MongoVideosRepository initialization errors."""
    config_mock = mocker.patch("src.analysis_service.run_worker.load_config")
    mocker.patch("src.analysis_service.run_worker.MongoClient")
    mock_mongo_videos_repo = mocker.patch("src.analysis_service.run_worker.MongoVideosRepository")
    mocker.patch("src.analysis_service.run_worker.MongoAnalysisRepository")
    mocker.patch("src.analysis_service.run_worker.SimpleWordCountBackend")
    mocker.patch("src.analysis_service.run_worker.RabbitMQAnalysisEventPublisher")
    mocker.patch("src.analysis_service.run_worker.RabbitMQTranscriptCreatedConsumer")
    mocker.patch("src.analysis_service.run_worker.MinioStorage")

    config_instance = config_mock.return_value
    config_instance.mongo_db_name = "test_db"

    mock_mongo_videos_repo.side_effect = Exception("Mongo Connection Error")

    with pytest.raises(Exception, match="Mongo Connection Error"):
        main()
