import pytest
from datetime import datetime
from src.shared.videos_repository import MongoVideosRepository
from src.shared.exceptions import VideoNotFoundError


@pytest.fixture
def repository(mongo_client):
    """Create a MongoVideosRepository instance with a clean database."""
    # Clear the videos collection before each test
    mongo_client["therapy_analysis"]["videos"].delete_many({})
    return MongoVideosRepository(client=mongo_client)


@pytest.fixture
def uploaded_video(mongo_client) -> dict:
    """Pre-populate a video document in uploaded status."""
    collection = mongo_client["therapy_analysis"]["videos"]
    doc = {
        "video_id": "video-1",
        "filename": "session1.mp4",
        "storage_path": "/data/uploads/video-1/session1.mp4",
        "status": "uploaded"
    }
    collection.insert_one(doc)
    return doc


@pytest.mark.unit
def test_should_insert_new_document_with_uploaded_status_on_upsert(repository, mongo_client) -> None:
    repository.upsert_on_upload(
        video_id="video-1",
        filename="session1.mp4",
        storage_path="/data/uploads/video-1/session1.mp4",
    )
    
    collection = mongo_client["therapy_analysis"]["videos"]
    documents = list(collection.find({"video_id": "video-1"}))
    
    assert len(documents) == 1
    doc = documents[0]
    assert doc["filename"] == "session1.mp4"
    assert doc["storage_path"] == "/data/uploads/video-1/session1.mp4"
    assert doc["status"] == "uploaded"


@pytest.mark.unit
def test_should_update_existing_document_without_duplicates_on_second_upsert(
    repository, mongo_client
) -> None:
    # First upsert
    repository.upsert_on_upload(
        video_id="video-1",
        filename="old_name.mp4",
        storage_path="/old/path",
    )
    
    # Second upsert (update)
    repository.upsert_on_upload(
        video_id="video-1",
        filename="new_name.mp4",
        storage_path="/new/path",
    )
    
    collection = mongo_client["therapy_analysis"]["videos"]
    documents = list(collection.find({"video_id": "video-1"}))
    doc = documents[0]
    
    assert len(documents) == 1
    assert doc["filename"] == "new_name.mp4"
    assert doc["storage_path"] == "/new/path"
    assert doc["status"] == "uploaded"


@pytest.mark.unit
def test_should_store_uploaded_at_timestamp_when_provided(repository, mongo_client) -> None:
    uploaded_at = datetime(2025, 1, 1, 12, 0, 0)
    
    repository.upsert_on_upload(
        video_id="video-1",
        filename="session1.mp4",
        storage_path="/data/uploads/video-1/session1.mp4",
        uploaded_at=uploaded_at,
    )
    
    collection = mongo_client["therapy_analysis"]["videos"]
    documents = list(collection.find({"video_id": "video-1"}))
    doc = documents[0]
    
    assert len(documents) == 1
    assert "uploaded_at" in doc
    assert doc["uploaded_at"] == uploaded_at


@pytest.mark.unit
def test_should_update_status_when_marking_analyzed(
    repository, mongo_client, uploaded_video
) -> None:
    repository.mark_analyzed(video_id="video-1")
    
    collection = mongo_client["therapy_analysis"]["videos"]
    doc = collection.find_one({"video_id": "video-1"})
    
    assert doc["status"] == "analyzed"
    assert doc["filename"] == "session1.mp4"  # Should remain unchanged


@pytest.mark.unit
def test_should_set_word_count_when_provided_to_mark_analyzed(
    repository, mongo_client, uploaded_video
) -> None:
    repository.mark_analyzed(video_id="video-1", word_count=123)
    
    collection = mongo_client["therapy_analysis"]["videos"]
    doc = collection.find_one({"video_id": "video-1"})
    
    assert doc["status"] == "analyzed"
    assert doc["word_count"] == 123


@pytest.mark.unit
def test_should_raise_error_when_marking_nonexistent_video_as_analyzed(
    repository, mongo_client
) -> None:
    with pytest.raises(VideoNotFoundError):
        repository.mark_analyzed(video_id="missing-video", word_count=999)
