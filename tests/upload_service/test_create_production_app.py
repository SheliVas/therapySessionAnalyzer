import pytest

from src.upload_service.app import create_production_app
from src.upload_service.storage import StorageClient
from src.upload_service.domain import VideoEventPublisher


# --- Unit Tests ---

@pytest.mark.unit
def test_should_pass_storage_and_publisher_to_create_app(mocker):
    """Verify create_production_app passes storage and publisher to create_app."""
    mock_minio_storage_class = mocker.patch("src.upload_service.app.MinioStorage")
    mock_rabbitmq_publisher_class = mocker.patch(
        "src.upload_service.app.RabbitMQVideoEventPublisher"
    )
    mock_create_app = mocker.patch("src.upload_service.app.create_app")
    mocker.patch("src.upload_service.app.get_minio_config")
    mocker.patch("src.upload_service.app.get_rabbitmq_config")
    
    mock_storage_instance = mocker.MagicMock(spec=StorageClient)
    mock_publisher_instance = mocker.MagicMock(spec=VideoEventPublisher)
    
    mock_minio_storage_class.return_value = mock_storage_instance
    mock_rabbitmq_publisher_class.return_value = mock_publisher_instance
    mock_create_app.return_value = mocker.MagicMock()
    
    create_production_app()
    
    mock_create_app.assert_called_once_with(
        storage_client=mock_storage_instance,
        publisher=mock_publisher_instance,
    )

@pytest.mark.unit
def test_should_call_get_minio_config(mocker):
    """Verify create_production_app calls get_minio_config to fetch MinIO settings."""
    mock_get_minio_config = mocker.patch("src.upload_service.app.get_minio_config")
    mocker.patch("src.upload_service.app.MinioStorage")
    mocker.patch("src.upload_service.app.RabbitMQVideoEventPublisher")
    mocker.patch("src.upload_service.app.get_rabbitmq_config")
    mocker.patch("src.upload_service.app.create_app")
    
    create_production_app()
    
    mock_get_minio_config.assert_called_once()


@pytest.mark.unit
def test_should_call_get_rabbitmq_config(mocker):
    """Verify create_production_app calls get_rabbitmq_config to fetch RabbitMQ settings."""
    mock_get_rabbitmq_config = mocker.patch("src.upload_service.app.get_rabbitmq_config")
    mocker.patch("src.upload_service.app.MinioStorage")
    mocker.patch("src.upload_service.app.RabbitMQVideoEventPublisher")
    mocker.patch("src.upload_service.app.get_minio_config")
    mocker.patch("src.upload_service.app.create_app")
    
    create_production_app()
    
    mock_get_rabbitmq_config.assert_called_once()


@pytest.mark.unit
def test_should_raise_error_when_minio_storage_init_fails(mocker):
    """Verify create_production_app propagates error if MinioStorage initialization fails."""
    mocker.patch("src.upload_service.app.get_minio_config")
    mocker.patch("src.upload_service.app.get_rabbitmq_config")
    mock_minio_storage_class = mocker.patch("src.upload_service.app.MinioStorage")
    mock_minio_storage_class.side_effect = Exception("Cannot connect to MinIO")
    
    with pytest.raises(Exception, match="Cannot connect to MinIO"):
        create_production_app()


@pytest.mark.unit
def test_should_raise_error_when_rabbitmq_publisher_init_fails(mocker):
    """Verify create_production_app propagates error if RabbitMQVideoEventPublisher init fails."""
    mocker.patch("src.upload_service.app.get_minio_config")
    mocker.patch("src.upload_service.app.get_rabbitmq_config")
    mocker.patch("src.upload_service.app.MinioStorage")
    mock_rabbitmq_publisher_class = mocker.patch("src.upload_service.app.RabbitMQVideoEventPublisher")
    mock_rabbitmq_publisher_class.side_effect = Exception("RabbitMQ connection refused")
    
    with pytest.raises(Exception, match="RabbitMQ connection refused"):
        create_production_app()


@pytest.mark.unit
def test_should_return_fastapi_app_instance(mocker):
    """Verify create_production_app returns a FastAPI app instance."""
    mocker.patch("src.upload_service.app.get_minio_config")
    mocker.patch("src.upload_service.app.get_rabbitmq_config")
    mocker.patch("src.upload_service.app.MinioStorage")
    mocker.patch("src.upload_service.app.RabbitMQVideoEventPublisher")
    mock_create_app = mocker.patch("src.upload_service.app.create_app")
    mock_app_instance = mocker.MagicMock()
    mock_create_app.return_value = mock_app_instance
    
    result = create_production_app()
    
    assert result is mock_app_instance


@pytest.mark.unit
def test_should_initialize_minio_with_config_object(mocker):
    """Verify create_production_app passes config object to MinioStorage constructor."""
    mock_config = mocker.MagicMock()
    mock_get_minio_config = mocker.patch(
        "src.upload_service.app.get_minio_config",
        return_value=mock_config
    )
    mock_minio_storage_class = mocker.patch("src.upload_service.app.MinioStorage")
    mocker.patch("src.upload_service.app.RabbitMQVideoEventPublisher")
    mocker.patch("src.upload_service.app.get_rabbitmq_config")
    mocker.patch("src.upload_service.app.create_app")
    
    create_production_app()
    
    mock_minio_storage_class.assert_called_once_with(mock_config)


@pytest.mark.unit
def test_should_initialize_rabbitmq_publisher_with_config_object(mocker):
    """Verify create_production_app passes config object to RabbitMQVideoEventPublisher."""
    mock_config = mocker.MagicMock()
    mock_get_rabbitmq_config = mocker.patch(
        "src.upload_service.app.get_rabbitmq_config",
        return_value=mock_config
    )
    mocker.patch("src.upload_service.app.MinioStorage")
    mock_rabbitmq_publisher_class = mocker.patch("src.upload_service.app.RabbitMQVideoEventPublisher")
    mocker.patch("src.upload_service.app.get_minio_config")
    mocker.patch("src.upload_service.app.create_app")
    
    create_production_app()
    
    mock_rabbitmq_publisher_class.assert_called_once_with(mock_config)