import pytest

from src.shared.minio_storage import MinioStorage
from src.shared.config import MinIOConfig


# --- Config Tests ---


@pytest.mark.unit
def test_minio_config_should_initialize_with_required_fields():
    """Verify MinIOConfig initializes with required endpoint, access_key, secret_key."""
    config = MinIOConfig(
        endpoint="localhost:9000",
        access_key="minioadmin",
        secret_key="minioadmin",
    )
    
    assert config.endpoint == "localhost:9000"
    assert config.access_key == "minioadmin"
    assert config.secret_key == "minioadmin"


@pytest.mark.unit
def test_minio_config_should_use_default_bucket_name():
    """Verify MinIOConfig uses default bucket name 'therapy-videos'."""
    config = MinIOConfig(
        endpoint="localhost:9000",
        access_key="minioadmin",
        secret_key="minioadmin",
    )
    
    assert config.bucket == "therapy-videos"


@pytest.mark.unit
def test_minio_config_should_use_default_secure_false():
    """Verify MinIOConfig defaults to secure=False."""
    config = MinIOConfig(
        endpoint="localhost:9000",
        access_key="minioadmin",
        secret_key="minioadmin",
    )
    
    assert config.secure is False


@pytest.mark.unit
def test_minio_config_should_allow_custom_bucket_name():
    """Verify MinIOConfig accepts custom bucket name."""
    config = MinIOConfig(
        endpoint="localhost:9000",
        access_key="minioadmin",
        secret_key="minioadmin",
        bucket="custom-bucket",
    )
    
    assert config.bucket == "custom-bucket"


@pytest.mark.unit
def test_minio_config_should_allow_secure_true():
    """Verify MinIOConfig accepts secure=True for HTTPS."""
    config = MinIOConfig(
        endpoint="minio.example.com:443",
        access_key="minioadmin",
        secret_key="minioadmin",
        secure=True,
    )
    
    assert config.secure is True


@pytest.mark.unit
def test_minio_config_should_store_all_fields():
    """Verify MinIOConfig stores all provided fields correctly."""
    config = MinIOConfig(
        endpoint="s3.example.com",
        access_key="AKIAIOSFODNN7EXAMPLE",
        secret_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        bucket="production-bucket",
        secure=True,
    )
    
    assert config.endpoint == "s3.example.com"
    assert config.access_key == "AKIAIOSFODNN7EXAMPLE"
    assert config.secret_key == "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
    assert config.bucket == "production-bucket"
    assert config.secure is True


# --- Fixtures ---


@pytest.fixture
def minio_config() -> MinIOConfig:
    return MinIOConfig(
        endpoint="localhost:9000",
        access_key="minioadmin",
        secret_key="minioadmin",
        bucket="therapy-videos",
    )


@pytest.fixture
def mock_minio_client(mocker):
    """Mock minio.Minio client."""
    return mocker.MagicMock()


@pytest.fixture
def minio_storage(minio_config, mocker):
    """Create MinioStorage with mocked Minio client."""
    mocker.patch("src.shared.minio_storage.Minio", return_value=mocker.MagicMock())
    storage = MinioStorage(minio_config)
    return storage


# --- Unit Tests ---


@pytest.mark.unit
def test_should_create_bucket_when_missing_on_upload(minio_config, mocker):
    """Verify upload_file creates bucket if it doesn't exist."""
    mock_client = mocker.MagicMock()
    mock_client.bucket_exists.return_value = False
    mocker.patch("src.shared.minio_storage.Minio", return_value=mock_client)
    
    storage = MinioStorage(minio_config)
    content = b"video data"
    
    storage.upload_file(bucket="therapy-videos", key="videos/123/test.mp4", content=content)
    
    mock_client.make_bucket.assert_called_once_with("therapy-videos")
    mock_client.put_object.assert_called_once()


@pytest.mark.unit
def test_should_put_object_with_correct_parameters(minio_config, mocker):
    """Verify upload_file calls put_object with correct bucket, key, and content length."""
    mock_client = mocker.MagicMock()
    mock_client.bucket_exists.return_value = True
    mocker.patch("src.shared.minio_storage.Minio", return_value=mock_client)
    
    storage = MinioStorage(minio_config)
    content = b"video data"
    bucket = "therapy-videos"
    key = "videos/123/test.mp4"
    
    storage.upload_file(bucket=bucket, key=key, content=content)
    
    call_args = mock_client.put_object.call_args
    assert call_args[1]["bucket_name"] == bucket
    assert call_args[1]["object_name"] == key
    assert call_args[1]["length"] == len(content)


@pytest.mark.unit
def test_should_skip_bucket_creation_when_exists(minio_config, mocker):
    """Verify bucket creation is skipped if bucket already exists."""
    mock_client = mocker.MagicMock()
    mock_client.bucket_exists.return_value = True
    mocker.patch("src.shared.minio_storage.Minio", return_value=mock_client)
    
    storage = MinioStorage(minio_config)
    content = b"video data"
    
    storage.upload_file(bucket="therapy-videos", key="videos/123/test.mp4", content=content)
    
    mock_client.make_bucket.assert_not_called()
    mock_client.put_object.assert_called_once()


@pytest.mark.unit
def test_should_download_file_and_return_bytes(minio_config, mocker):
    """Verify download_file fetches object and returns raw bytes."""
    mock_response = mocker.MagicMock()
    mock_response.read.return_value = b"video data"
    
    mock_client = mocker.MagicMock()
    mock_client.get_object.return_value = mock_response
    mocker.patch("src.shared.minio_storage.Minio", return_value=mock_client)
    
    storage = MinioStorage(minio_config)
    bucket = "therapy-videos"
    key = "videos/123/test.mp4"
    
    result = storage.download_file(bucket=bucket, key=key)
    
    assert result == b"video data"
    mock_client.get_object.assert_called_once_with(bucket, key)


@pytest.mark.unit
def test_should_raise_error_when_object_missing_on_download(minio_config, mocker):
    """Verify download_file raises ValueError when object is missing."""
    mock_client = mocker.MagicMock()
    mock_client.get_object.side_effect = Exception("NoSuchKey")
    mocker.patch("src.shared.minio_storage.Minio", return_value=mock_client)
    
    storage = MinioStorage(minio_config)
    
    with pytest.raises(ValueError, match="Object not found"):
        storage.download_file(bucket="therapy-videos", key="videos/nonexistent/test.mp4")


@pytest.mark.unit
def test_should_create_minio_client_with_config_parameters(minio_config, mocker):
    """Verify MinioStorage initializes Minio client with correct parameters."""
    mock_minio_class = mocker.patch("src.shared.minio_storage.Minio")
    
    storage = MinioStorage(minio_config)
    
    mock_minio_class.assert_called_once_with(
        endpoint=minio_config.endpoint,
        access_key=minio_config.access_key,
        secret_key=minio_config.secret_key,
        secure=False,
    )


@pytest.mark.unit
def test_should_raise_error_when_bucket_creation_fails(minio_config, mocker):
    """Verify upload_file propagates error when bucket creation fails."""
    mock_client = mocker.MagicMock()
    mock_client.bucket_exists.return_value = False
    mock_client.make_bucket.side_effect = Exception("Permission denied")
    mocker.patch("src.shared.minio_storage.Minio", return_value=mock_client)
    
    storage = MinioStorage(minio_config)
    
    with pytest.raises(Exception):
        storage.upload_file(bucket="therapy-videos", key="videos/123/test.mp4", content=b"data")


@pytest.mark.unit
def test_should_raise_error_when_put_object_fails(minio_config, mocker):
    """Verify upload_file propagates error when put_object fails."""
    mock_client = mocker.MagicMock()
    mock_client.bucket_exists.return_value = True
    mock_client.put_object.side_effect = Exception("Upload failed")
    mocker.patch("src.shared.minio_storage.Minio", return_value=mock_client)
    
    storage = MinioStorage(minio_config)
    
    with pytest.raises(Exception):
        storage.upload_file(bucket="therapy-videos", key="videos/123/test.mp4", content=b"data")


@pytest.mark.unit
def test_should_handle_large_file_upload(minio_config, mocker):
    """Verify upload_file correctly handles large file with proper length."""
    mock_client = mocker.MagicMock()
    mock_client.bucket_exists.return_value = True
    mocker.patch("src.shared.minio_storage.Minio", return_value=mock_client)
    
    storage = MinioStorage(minio_config)
    large_content = b"x" * (100 * 1024 * 1024)  # 100MB
    
    storage.upload_file(bucket="therapy-videos", key="videos/123/large.mp4", content=large_content)
    
    call_args = mock_client.put_object.call_args
    assert call_args[1]["length"] == len(large_content)
    assert call_args[1]["length"] == 100 * 1024 * 1024


@pytest.mark.unit
def test_should_handle_special_characters_in_key(minio_config, mocker):
    """Verify upload_file handles special characters in object key."""
    mock_client = mocker.MagicMock()
    mock_client.bucket_exists.return_value = True
    mocker.patch("src.shared.minio_storage.Minio", return_value=mock_client)
    
    storage = MinioStorage(minio_config)
    special_key = "videos/123/test-video_2025.01.15_session@1.mp4"
    
    storage.upload_file(bucket="therapy-videos", key=special_key, content=b"data")
    
    call_args = mock_client.put_object.call_args
    assert call_args[1]["object_name"] == special_key


@pytest.mark.unit
def test_should_handle_multiple_buckets(minio_config, mocker):
    """Verify upload_file can handle uploads to different buckets."""
    mock_client = mocker.MagicMock()
    mock_client.bucket_exists.return_value = False
    mocker.patch("src.shared.minio_storage.Minio", return_value=mock_client)
    
    storage = MinioStorage(minio_config)
    
    storage.upload_file(bucket="bucket-1", key="videos/123/test.mp4", content=b"data1")
    storage.upload_file(bucket="bucket-2", key="videos/456/test.mp4", content=b"data2")
    
    assert mock_client.make_bucket.call_count == 2
    calls = [call[0][0] for call in mock_client.make_bucket.call_args_list]
    assert "bucket-1" in calls
    assert "bucket-2" in calls


@pytest.mark.unit
def test_should_raise_error_when_download_fails(minio_config, mocker):
    """Verify download_file propagates error from get_object."""
    mock_client = mocker.MagicMock()
    mock_client.get_object.side_effect = Exception("Connection timeout")
    mocker.patch("src.shared.minio_storage.Minio", return_value=mock_client)
    
    storage = MinioStorage(minio_config)
    
    with pytest.raises(Exception):
        storage.download_file(bucket="therapy-videos", key="videos/123/test.mp4")


@pytest.mark.unit
def test_should_handle_empty_bytes_download(minio_config, mocker):
    """Verify download_file handles empty file correctly."""
    mock_response = mocker.MagicMock()
    mock_response.read.return_value = b""
    
    mock_client = mocker.MagicMock()
    mock_client.get_object.return_value = mock_response
    mocker.patch("src.shared.minio_storage.Minio", return_value=mock_client)
    
    storage = MinioStorage(minio_config)
    
    result = storage.download_file(bucket="therapy-videos", key="videos/123/empty.mp4")
    
    assert result == b""
    assert len(result) == 0
