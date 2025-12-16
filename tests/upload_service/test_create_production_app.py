import pytest
from src.upload_service.app import create_production_app
from src.upload_service.domain import VideoEventPublisher, VideosRepository

# --- Fixtures ---

@pytest.fixture
def mock_dependencies(mocker):
    """Mock all external dependencies for create_production_app."""
    mocks = {}
    
    # Config mocks
    mocks["minio_config"] = mocker.patch("src.upload_service.app.get_minio_config")
    mocks["rabbitmq_config"] = mocker.patch("src.upload_service.app.get_rabbitmq_config")
    mocks["mongo_config"] = mocker.patch("src.upload_service.app.get_mongo_config")
    
    # Service mocks
    mocks["minio_storage"] = mocker.patch("src.upload_service.app.MinioStorage")
    mocks["rabbitmq_publisher"] = mocker.patch("src.upload_service.app.RabbitMQVideoEventPublisher")
    mocks["mongo_repo"] = mocker.patch("src.upload_service.app.MongoVideosRepository")
    
    # External lib mocks
    mocks["mongo_client"] = mocker.patch("src.upload_service.app.MongoClient")
    
    # App mock
    mocks["create_app"] = mocker.patch("src.upload_service.app.create_app")
    
    return mocks

# --- Unit Tests ---

@pytest.mark.unit
def test_should_pass_all_dependencies_to_create_app(mock_dependencies):
    """Verify create_production_app passes all dependencies to create_app."""

    storage_instance = mock_dependencies["minio_storage"].return_value
    publisher_instance = mock_dependencies["rabbitmq_publisher"].return_value
    repo_instance = mock_dependencies["mongo_repo"].return_value
    
    create_production_app()
    
    mock_dependencies["create_app"].assert_called_once_with(
        storage_client=storage_instance,
        publisher=publisher_instance,
        repository=repo_instance,
    )

@pytest.mark.unit
def test_should_initialize_minio_correctly(mock_dependencies):
    """Verify MinioStorage is initialized with config."""
    config = mock_dependencies["minio_config"].return_value
    
    create_production_app()
    
    mock_dependencies["minio_storage"].assert_called_once_with(config)

@pytest.mark.unit
def test_should_initialize_rabbitmq_publisher_correctly(mock_dependencies):
    """Verify RabbitMQVideoEventPublisher is initialized with config."""
    config = mock_dependencies["rabbitmq_config"].return_value
    
    create_production_app()
    
    mock_dependencies["rabbitmq_publisher"].assert_called_once_with(config)

@pytest.mark.unit
def test_should_initialize_mongo_repository_correctly(mock_dependencies):
    """Verify MongoVideosRepository is initialized with client and db_name."""
    config = mock_dependencies["mongo_config"].return_value
    client = mock_dependencies["mongo_client"].return_value
    
    create_production_app()
    
    mock_dependencies["mongo_client"].assert_called_once_with(config.uri)
    mock_dependencies["mongo_repo"].assert_called_once_with(client, config.db_name)

@pytest.mark.unit
def test_should_return_fastapi_app_instance(mock_dependencies):
    """Verify create_production_app returns the app instance."""
    expected_app = mock_dependencies["create_app"].return_value
    
    result = create_production_app()
    
    assert result is expected_app

@pytest.mark.unit
@pytest.mark.parametrize(
    "mock_key, error_message",
    [
        ("minio_config", "MinIO Config Error"),
        ("rabbitmq_config", "RabbitMQ Config Error"),
        ("mongo_config", "Mongo Config Error"),
        ("minio_storage", "MinIO Init Error"),
        ("rabbitmq_publisher", "Publisher Init Error"),
        ("mongo_client", "Mongo Client Error"),
        ("mongo_repo", "Repo Init Error"),
    ],
)
def test_should_raise_error_when_dependency_initialization_fails(
    mock_dependencies, mock_key, error_message
):
    """Verify create_production_app propagates errors from all dependencies."""
    mock_dependencies[mock_key].side_effect = Exception(error_message)
    
    with pytest.raises(Exception, match=error_message):
        create_production_app()


@pytest.mark.unit
def test_should_create_distinct_instances_for_each_call(mock_dependencies):
    """Verify create_production_app creates distinct instances on each call."""
    mock_dependencies["mongo_client"].side_effect = [object(), object()]
    mock_dependencies["mongo_repo"].side_effect = [object(), object()]
    
    create_production_app()
    create_production_app()
    
    assert mock_dependencies["mongo_client"].call_count == 2
    assert mock_dependencies["mongo_repo"].call_count == 2
