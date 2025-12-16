import pytest
from fastapi.testclient import TestClient
from io import BytesIO

from src.upload_service.app import create_app
from src.upload_service.domain import VideoEventPublisher, VideosRepository, StorageClient


# --- Fixtures ---


@pytest.fixture
def fake_storage(mocker):
    """Fake storage client."""
    return mocker.MagicMock(spec=StorageClient)


@pytest.fixture
def fake_publisher(mocker):
    """Fake event publisher."""
    return mocker.MagicMock(spec=VideoEventPublisher)


@pytest.fixture
def fake_repository(mocker):
    """Fake videos repository."""
    return mocker.MagicMock(spec=VideosRepository)


@pytest.fixture
def client(fake_storage, fake_publisher, fake_repository):
    """Create test client with fake dependencies."""
    app = create_app(
        storage_client=fake_storage,
        publisher=fake_publisher,
        repository=fake_repository,
    )
    return TestClient(app)


# --- Unit Tests ---


@pytest.mark.unit
@pytest.mark.parametrize(
    "dependency_fixture, method_name, error_message",
    [
        ("fake_repository", "upsert_on_upload", "Database connection failed"),
        ("fake_storage", "upload_file", "MinIO unavailable"),
        ("fake_publisher", "publish_video_uploaded", "RabbitMQ unavailable"),
    ],
)
def test_should_return_500_when_dependency_fails(
    client, request, dependency_fixture, method_name, error_message
):
    """Verify endpoint returns 500 when any dependency fails."""
    dependency = request.getfixturevalue(dependency_fixture)
    
    getattr(dependency, method_name).side_effect = Exception(error_message)
    
    response = client.post(
        "/videos",
        files={"file": ("test.mp4", b"video data")},
    )
    
    assert response.status_code == 500


@pytest.mark.unit
def test_should_return_400_for_empty_file(client):
    """Verify endpoint returns 400 for empty file upload."""
    response = client.post(
        "/videos",
        files={"file": ("test.mp4", b"")},
    )
    
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


@pytest.mark.unit
def test_should_call_repository_on_successful_upload(client, fake_repository):
    """Verify repository is called on successful file upload."""
    response = client.post(
        "/videos",
        files={"file": ("test.mp4", b"video data")},
    )
    
    assert response.status_code == 201
    fake_repository.upsert_on_upload.assert_called_once()


@pytest.mark.unit
def test_should_return_video_id_and_filename_on_success(client):
    """Verify endpoint returns video_id and filename on successful upload."""
    response = client.post(
        "/videos",
        files={"file": ("test.mp4", b"video data")},
    )
    
    assert response.status_code == 201
    data = response.json()
    assert "video_id" in data
    assert data["filename"] == "test.mp4"


@pytest.mark.unit
def test_should_accept_large_file_upload(fake_storage, fake_publisher, fake_repository):
    """Verify handling of large file uploads."""
    client = TestClient(create_app(fake_storage, fake_publisher, fake_repository))
    large_content = b"x" * (10 * 1024 * 1024)  # 10MB
    
    response = client.post(
        "/videos",
        files={"file": ("large_test.mp4", BytesIO(large_content))},
    )
    
    assert response.status_code == 201
    fake_repository.upsert_on_upload.assert_called_once()


@pytest.mark.unit
def test_should_handle_unicode_filename_in_upload(
    fake_storage, fake_publisher, fake_repository
):
    """Verify unicode filenames are handled correctly."""
    client = TestClient(create_app(fake_storage, fake_publisher, fake_repository))
    
    response = client.post(
        "/videos",
        files={"file": ("療法_2025.mp4", b"video data")},
    )
    
    assert response.status_code == 201
    call_kwargs = fake_repository.upsert_on_upload.call_args.kwargs
    assert call_kwargs["filename"] == "療法_2025.mp4"


@pytest.mark.unit
def test_should_return_422_on_missing_file_field(fake_storage, fake_publisher, fake_repository):
    """Verify 422 response when file field is missing (FastAPI validation)."""
    client = TestClient(create_app(fake_storage, fake_publisher, fake_repository))
    
    response = client.post("/videos", data={})
    
    assert response.status_code == 422


@pytest.mark.unit
def test_should_not_call_storage_on_empty_file(
    fake_storage, fake_publisher, fake_repository
):
    """Verify empty file upload is rejected without calling storage."""
    client = TestClient(create_app(fake_storage, fake_publisher, fake_repository))
    
    response = client.post(
        "/videos",
        files={"file": ("empty.mp4", b"")},
    )
    
    assert response.status_code == 400
    fake_storage.upload_file.assert_not_called()


@pytest.mark.unit
def test_should_handle_very_long_filename(fake_storage, fake_publisher, fake_repository):
    """Verify handling of very long filenames."""
    client = TestClient(create_app(fake_storage, fake_publisher, fake_repository))
    long_filename = "a" * 500 + ".mp4"
    
    response = client.post(
        "/videos",
        files={"file": (long_filename, b"video data")},
    )
    
    assert response.status_code == 201
    call_kwargs = fake_repository.upsert_on_upload.call_args.kwargs
    assert call_kwargs["filename"] == long_filename


@pytest.mark.unit
def test_should_return_different_video_ids_for_multiple_uploads(
    fake_storage, fake_publisher, fake_repository
):
    """Verify each upload gets a unique video_id."""
    client = TestClient(create_app(fake_storage, fake_publisher, fake_repository))
    
    response1 = client.post(
        "/videos",
        files={"file": ("test1.mp4", b"video data")},
    )
    response2 = client.post(
        "/videos",
        files={"file": ("test2.mp4", b"video data")},
    )
    
    assert response1.status_code == 201
    assert response2.status_code == 201
    
    video_id_1 = response1.json()["video_id"]
    video_id_2 = response2.json()["video_id"]
    
    assert video_id_1 != video_id_2


@pytest.mark.unit
@pytest.mark.parametrize(
    "filename,expected_sanitized_substring",
    [
        ("session@#$.mp4", "session___.mp4"),
        ("file!@#$%^&*.mov", "file________.mov"),
        ("normal_file.avi", "normal_file.avi"),
        ("test (1) [backup].mp4", "test__1___backup_.mp4"),
    ]
)
def test_should_sanitize_special_characters_in_filename(
    client,
    fake_repository,
    filename,
    expected_sanitized_substring,
):
    """Verify filename sanitization for various inputs."""
    response = client.post(
        "/videos",
        files={"file": (filename, b"video data")},
    )
    
    assert response.status_code == 201
    
    call_kwargs = fake_repository.upsert_on_upload.call_args.kwargs
    storage_path = call_kwargs["storage_path"]
    assert expected_sanitized_substring in storage_path
