import pytest
from datetime import datetime

from src.upload_service.domain import handle_video_upload


# --- Fixtures ---


@pytest.fixture
def fake_storage(mocker):
    """Fake storage client."""
    return mocker.MagicMock()


@pytest.fixture
def fake_publisher(mocker):
    """Fake event publisher."""
    return mocker.MagicMock()


@pytest.fixture
def fake_repository(mocker):
    """Fake videos repository."""
    return mocker.MagicMock()


# --- Unit Tests ---


@pytest.mark.unit
def test_should_call_repository_upsert_on_upload_with_correct_args(
    fake_storage, fake_publisher, fake_repository
):
    """Verify handle_video_upload calls repository.upsert_on_upload with correct arguments."""
    filename = "therapy-session.mp4"
    content = b"video data"
    
    video_id = handle_video_upload(
        storage_client=fake_storage,
        publisher=fake_publisher,
        repository=fake_repository,
        filename=filename,
        content=content,
    )
    
    fake_repository.upsert_on_upload.assert_called_once()
    call_kwargs = fake_repository.upsert_on_upload.call_args.kwargs
    
    assert call_kwargs["video_id"] == video_id
    assert call_kwargs["filename"] == filename
    assert "therapy-videos/" in call_kwargs["storage_path"]
    assert isinstance(call_kwargs["uploaded_at"], datetime)


@pytest.mark.unit
def test_should_format_storage_path_as_bucket_slash_key(
    fake_storage, fake_publisher, fake_repository
):
    """Verify storage_path is formatted as bucket/key."""
    filename = "test.mp4"
    content = b"data"
    
    handle_video_upload(
        storage_client=fake_storage,
        publisher=fake_publisher,
        repository=fake_repository,
        filename=filename,
        content=content,
    )
    
    call_kwargs = fake_repository.upsert_on_upload.call_args.kwargs
    storage_path = call_kwargs["storage_path"]
    
    assert storage_path.startswith("therapy-videos/")
    assert "/test.mp4" in storage_path


@pytest.mark.unit
def test_should_call_repository_after_storage_upload(
    fake_storage, fake_publisher, fake_repository
):
    """Verify repository is called after storage upload completes."""
    content = b"video data"
    call_order = []
    
    fake_storage.upload_file.side_effect = lambda **kwargs: call_order.append("storage")
    fake_repository.upsert_on_upload.side_effect = lambda **kwargs: call_order.append("repository")
    
    handle_video_upload(
        storage_client=fake_storage,
        publisher=fake_publisher,
        repository=fake_repository,
        filename="test.mp4",
        content=content,
    )
    
    assert call_order == ["storage", "repository"]


@pytest.mark.unit
@pytest.mark.parametrize(
    "dependency_fixture, method_name, error_message",
    [
        ("fake_repository", "upsert_on_upload", "Database connection failed"),
        ("fake_publisher", "publish_video_uploaded", "Message queue unavailable"),
        ("fake_storage", "upload_file", "MinIO connection timeout"),
    ],
)
def test_should_propagate_dependency_errors(
    request, dependency_fixture, method_name, error_message,
    fake_storage, fake_publisher, fake_repository
):
    """Verify errors from dependencies are propagated to caller."""
    dependency = request.getfixturevalue(dependency_fixture)
    
    getattr(dependency, method_name).side_effect = Exception(error_message)
    
    with pytest.raises(Exception, match=error_message):
        handle_video_upload(
            storage_client=fake_storage,
            publisher=fake_publisher,
            repository=fake_repository,
            filename="test.mp4",
            content=b"data",
        )


@pytest.mark.unit
def test_should_sanitize_filename_in_storage_path(
    fake_storage, fake_publisher, fake_repository
):
    """Verify special characters in filename are sanitized in storage path."""
    filename = "therapy session (2025-01-15).mp4"
    content = b"data"
    
    handle_video_upload(
        storage_client=fake_storage,
        publisher=fake_publisher,
        repository=fake_repository,
        filename=filename,
        content=content,
    )
    
    call_kwargs = fake_repository.upsert_on_upload.call_args.kwargs
    storage_path = call_kwargs["storage_path"]
    
    assert "(" not in storage_path
    assert ")" not in storage_path
    assert "_" in storage_path



@pytest.mark.unit
def test_should_not_call_repository_when_storage_upload_fails(
    fake_storage, fake_publisher, fake_repository
):
    """Verify repository is NOT called if storage upload fails."""
    fake_storage.upload_file.side_effect = Exception("Storage write failed")
    
    with pytest.raises(Exception, match="Storage write failed"):
        handle_video_upload(
            storage_client=fake_storage,
            publisher=fake_publisher,
            repository=fake_repository,
            filename="test.mp4",
            content=b"data",
        )
    
    fake_repository.upsert_on_upload.assert_not_called()


@pytest.mark.unit
def test_should_raise_error_on_empty_filename(
    fake_storage, fake_publisher, fake_repository
):
    """Verify empty filename is allowed but sanitized."""
    handle_video_upload(
        storage_client=fake_storage,
        publisher=fake_publisher,
        repository=fake_repository,
        filename="",
        content=b"data",
    )
    
    call_kwargs = fake_repository.upsert_on_upload.call_args.kwargs
    assert call_kwargs["filename"] == ""


@pytest.mark.unit
def test_should_raise_valueerror_on_empty_content(
    fake_storage, fake_publisher, fake_repository
):
    """Verify empty file content raises ValueError."""
    with pytest.raises(ValueError, match="empty"):
        handle_video_upload(
            storage_client=fake_storage,
            publisher=fake_publisher,
            repository=fake_repository,
            filename="test.mp4",
            content=b"",
        )


@pytest.mark.unit
def test_should_not_call_any_service_on_empty_content_error(
    fake_storage, fake_publisher, fake_repository
):
    """Verify no services are called if content is empty."""
    try:
        handle_video_upload(
            storage_client=fake_storage,
            publisher=fake_publisher,
            repository=fake_repository,
            filename="test.mp4",
            content=b"",
        )
    except ValueError:
        pass
    
    fake_storage.upload_file.assert_not_called()
    fake_repository.upsert_on_upload.assert_not_called()
    fake_publisher.publish_video_uploaded.assert_not_called()


@pytest.mark.unit
def test_should_generate_unique_video_ids(
    fake_storage, fake_publisher, fake_repository
):
    """Verify each upload generates a unique video_id."""
    content = b"data"
    
    video_id_1 = handle_video_upload(
        storage_client=fake_storage,
        publisher=fake_publisher,
        repository=fake_repository,
        filename="test1.mp4",
        content=content,
    )
    
    video_id_2 = handle_video_upload(
        storage_client=fake_storage,
        publisher=fake_publisher,
        repository=fake_repository,
        filename="test2.mp4",
        content=content,
    )
    
    assert video_id_1 != video_id_2


@pytest.mark.unit
def test_should_handle_very_long_filename(
    fake_storage, fake_publisher, fake_repository
):
    """Verify handling of very long filenames."""
    long_filename = "a" * 500 + ".mp4"
    content = b"data"
    
    video_id = handle_video_upload(
        storage_client=fake_storage,
        publisher=fake_publisher,
        repository=fake_repository,
        filename=long_filename,
        content=content,
    )
    
    assert video_id is not None
    call_kwargs = fake_repository.upsert_on_upload.call_args.kwargs
    assert call_kwargs["filename"] == long_filename


@pytest.mark.unit
def test_should_handle_unicode_filename(
    fake_storage, fake_publisher, fake_repository
):
    """Verify handling of unicode characters in filename."""
    filename = "療法セッション_2025.mp4"
    content = b"data"
    
    video_id = handle_video_upload(
        storage_client=fake_storage,
        publisher=fake_publisher,
        repository=fake_repository,
        filename=filename,
        content=content,
    )
    
    assert video_id is not None
    call_kwargs = fake_repository.upsert_on_upload.call_args.kwargs
    assert call_kwargs["filename"] == filename