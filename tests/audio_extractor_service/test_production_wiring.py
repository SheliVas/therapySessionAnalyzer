"""Tests for production wiring: repository creation and setup."""
import pytest
from datetime import datetime
from pathlib import Path

from src.upload_service.domain import VideoUploadedEvent
from src.audio_extractor_service.run_worker import create_production_app


# --- Helpers ---

def _create_video_uploaded_event(video_id: str) -> VideoUploadedEvent:
    """Helper to create a VideoUploadedEvent."""
    return VideoUploadedEvent(
        video_id=video_id,
        filename="test.mp4",
        bucket="therapy-videos",
        key=f"videos/{video_id}/test.mp4",
        uploaded_at=datetime.now(),
    )


# --- Unit Tests: Production App Wiring ---

@pytest.mark.unit
def test_should_create_production_app_with_dependencies(
    monkeypatch,
    tmp_path,
):
    """Production app should be creatable with required environment variables."""
    monkeypatch.setenv("RABBITMQ_HOST", "localhost")
    monkeypatch.setenv("RABBITMQ_PORT", "5672")
    monkeypatch.setenv("RABBITMQ_USER", "guest")
    monkeypatch.setenv("RABBITMQ_PASS", "guest")
    monkeypatch.setenv("AUDIO_EXTRACTED_QUEUE", "audio.extracted")
    monkeypatch.setenv("AUDIO_OUTPUT_BASE_DIR", str(tmp_path))
    monkeypatch.setenv("MINIO_ENDPOINT", "minio:9000")
    monkeypatch.setenv("MINIO_ACCESS_KEY", "minioadmin")
    monkeypatch.setenv("MINIO_SECRET_KEY", "minioadmin")
    monkeypatch.setenv("MONGO_URI", "mongodb://localhost:27017")
    monkeypatch.setenv("MONGO_DB", "therapy_analysis")
    
    result = create_production_app()
    
    assert result is not None


@pytest.mark.unit
def test_should_build_minio_storage_from_env(
    monkeypatch,
    tmp_path,
):
    """Production app should build MinioStorage from env variables."""
    monkeypatch.setenv("RABBITMQ_HOST", "localhost")
    monkeypatch.setenv("RABBITMQ_PORT", "5672")
    monkeypatch.setenv("RABBITMQ_USER", "guest")
    monkeypatch.setenv("RABBITMQ_PASS", "guest")
    monkeypatch.setenv("AUDIO_EXTRACTED_QUEUE", "audio.extracted")
    monkeypatch.setenv("AUDIO_OUTPUT_BASE_DIR", str(tmp_path))
    monkeypatch.setenv("MINIO_ENDPOINT", "minio:9000")
    monkeypatch.setenv("MINIO_ACCESS_KEY", "minioadmin")
    monkeypatch.setenv("MINIO_SECRET_KEY", "minioadmin")
    monkeypatch.setenv("MONGO_URI", "mongodb://localhost:27017")
    monkeypatch.setenv("MONGO_DB", "therapy_analysis")
    
    result = create_production_app()
    
    assert result["storage_client"] is not None


@pytest.mark.unit
def test_should_build_mongo_repository_from_env(
    monkeypatch,
    tmp_path,
):
    """Production app should build MongoVideosRepository from env variables."""
    monkeypatch.setenv("RABBITMQ_HOST", "localhost")
    monkeypatch.setenv("RABBITMQ_PORT", "5672")
    monkeypatch.setenv("RABBITMQ_USER", "guest")
    monkeypatch.setenv("RABBITMQ_PASS", "guest")
    monkeypatch.setenv("AUDIO_EXTRACTED_QUEUE", "audio.extracted")
    monkeypatch.setenv("AUDIO_OUTPUT_BASE_DIR", str(tmp_path))
    monkeypatch.setenv("MINIO_ENDPOINT", "minio:9000")
    monkeypatch.setenv("MINIO_ACCESS_KEY", "minioadmin")
    monkeypatch.setenv("MINIO_SECRET_KEY", "minioadmin")
    monkeypatch.setenv("MONGO_URI", "mongodb://localhost:27017")
    monkeypatch.setenv("MONGO_DB", "therapy_analysis")
    
    result = create_production_app()
    
    assert result["repository"] is not None


@pytest.mark.unit
def test_should_use_mongo_db_name_from_env(
    monkeypatch,
    tmp_path,
):
    """Production app should use MONGO_DB env var for database name."""
    monkeypatch.setenv("RABBITMQ_HOST", "localhost")
    monkeypatch.setenv("RABBITMQ_PORT", "5672")
    monkeypatch.setenv("RABBITMQ_USER", "guest")
    monkeypatch.setenv("RABBITMQ_PASS", "guest")
    monkeypatch.setenv("AUDIO_EXTRACTED_QUEUE", "audio.extracted")
    monkeypatch.setenv("AUDIO_OUTPUT_BASE_DIR", str(tmp_path))
    monkeypatch.setenv("MINIO_ENDPOINT", "minio:9000")
    monkeypatch.setenv("MINIO_ACCESS_KEY", "minioadmin")
    monkeypatch.setenv("MINIO_SECRET_KEY", "minioadmin")
    monkeypatch.setenv("MONGO_URI", "mongodb://localhost:27017")
    monkeypatch.setenv("MONGO_DB", "custom_db_name")
    
    result = create_production_app()
    
    assert result["repository"] is not None


@pytest.mark.unit
@pytest.mark.parametrize("env_var", [
    "RABBITMQ_HOST",
    "RABBITMQ_PORT",
    "RABBITMQ_USER",
    "RABBITMQ_PASS",
    "MINIO_ENDPOINT",
    "MINIO_ACCESS_KEY",
    "MINIO_SECRET_KEY",
    "MONGO_URI",
    "MONGO_DB",
])
def test_should_require_environment_variables(
    monkeypatch,
    tmp_path,
    env_var: str,
):
    """Production app should require all necessary environment variables."""
    monkeypatch.setenv("RABBITMQ_HOST", "localhost")
    monkeypatch.setenv("RABBITMQ_PORT", "5672")
    monkeypatch.setenv("RABBITMQ_USER", "guest")
    monkeypatch.setenv("RABBITMQ_PASS", "guest")
    monkeypatch.setenv("AUDIO_EXTRACTED_QUEUE", "audio.extracted")
    monkeypatch.setenv("AUDIO_OUTPUT_BASE_DIR", str(tmp_path))
    monkeypatch.setenv("MINIO_ENDPOINT", "minio:9000")
    monkeypatch.setenv("MINIO_ACCESS_KEY", "minioadmin")
    monkeypatch.setenv("MINIO_SECRET_KEY", "minioadmin")
    monkeypatch.setenv("MONGO_URI", "mongodb://localhost:27017")
    monkeypatch.setenv("MONGO_DB", "therapy_analysis")
    
    monkeypatch.delenv(env_var)
    
    with pytest.raises(KeyError):
        create_production_app()


@pytest.mark.unit
def test_should_return_dict_with_all_dependencies(
    monkeypatch,
    tmp_path,
):
    """Production app should return a dict with all required dependencies."""
    monkeypatch.setenv("RABBITMQ_HOST", "localhost")
    monkeypatch.setenv("RABBITMQ_PORT", "5672")
    monkeypatch.setenv("RABBITMQ_USER", "guest")
    monkeypatch.setenv("RABBITMQ_PASS", "guest")
    monkeypatch.setenv("AUDIO_EXTRACTED_QUEUE", "audio.extracted")
    monkeypatch.setenv("AUDIO_OUTPUT_BASE_DIR", str(tmp_path))
    monkeypatch.setenv("MINIO_ENDPOINT", "minio:9000")
    monkeypatch.setenv("MINIO_ACCESS_KEY", "minioadmin")
    monkeypatch.setenv("MINIO_SECRET_KEY", "minioadmin")
    monkeypatch.setenv("MONGO_URI", "mongodb://localhost:27017")
    monkeypatch.setenv("MONGO_DB", "therapy_analysis")
    
    result = create_production_app()
    
    assert isinstance(result, dict)
    assert "storage_client" in result
    assert "repository" in result
    assert "publisher" in result
    assert "consumer" in result


@pytest.mark.unit
def test_repository_should_be_mongo_instance(
    monkeypatch,
    tmp_path,
):
    """Repository returned should be MongoVideosRepository instance."""
    monkeypatch.setenv("RABBITMQ_HOST", "localhost")
    monkeypatch.setenv("RABBITMQ_PORT", "5672")
    monkeypatch.setenv("RABBITMQ_USER", "guest")
    monkeypatch.setenv("RABBITMQ_PASS", "guest")
    monkeypatch.setenv("AUDIO_EXTRACTED_QUEUE", "audio.extracted")
    monkeypatch.setenv("AUDIO_OUTPUT_BASE_DIR", str(tmp_path))
    monkeypatch.setenv("MINIO_ENDPOINT", "minio:9000")
    monkeypatch.setenv("MINIO_ACCESS_KEY", "minioadmin")
    monkeypatch.setenv("MINIO_SECRET_KEY", "minioadmin")
    monkeypatch.setenv("MONGO_URI", "mongodb://localhost:27017")
    monkeypatch.setenv("MONGO_DB", "therapy_analysis")
    
    result = create_production_app()
    
    assert hasattr(result["repository"], "mark_audio_extracted")


@pytest.mark.unit
def test_storage_client_should_be_minio_instance(
    monkeypatch,
    tmp_path,
):
    """Storage client returned should be MinioStorage instance."""
    monkeypatch.setenv("RABBITMQ_HOST", "localhost")
    monkeypatch.setenv("RABBITMQ_PORT", "5672")
    monkeypatch.setenv("RABBITMQ_USER", "guest")
    monkeypatch.setenv("RABBITMQ_PASS", "guest")
    monkeypatch.setenv("AUDIO_EXTRACTED_QUEUE", "audio.extracted")
    monkeypatch.setenv("AUDIO_OUTPUT_BASE_DIR", str(tmp_path))
    monkeypatch.setenv("MINIO_ENDPOINT", "minio:9000")
    monkeypatch.setenv("MINIO_ACCESS_KEY", "minioadmin")
    monkeypatch.setenv("MINIO_SECRET_KEY", "minioadmin")
    monkeypatch.setenv("MONGO_URI", "mongodb://localhost:27017")
    monkeypatch.setenv("MONGO_DB", "therapy_analysis")
    
    result = create_production_app()
    
    assert hasattr(result["storage_client"], "download_file")
    assert hasattr(result["storage_client"], "upload_file")
