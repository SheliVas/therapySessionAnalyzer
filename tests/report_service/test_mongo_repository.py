import pytest
from src.report_service.mongo_repository import VideoSummary, MongoReportRepository


@pytest.fixture
def sample_documents():
    return [
        {
            "video_id": "video-1",
            "word_count": 10,
            "extra": {"foo": "bar"}
        },
        {
            "video_id": "video-2",
            "word_count": 20,
            "extra": {"foo": "baz"}
        }
    ]


@pytest.fixture
def repository_with_data(mongo_client, sample_documents):
    db = mongo_client["therapy_analysis"]
    col = db["analysis_results"]
    col.insert_many(sample_documents)
    return MongoReportRepository(mongo_client)


def test_should_list_all_videos_when_collection_has_documents(repository_with_data, sample_documents):
    videos = repository_with_data.list_videos()
    
    assert len(videos) == 2, f"expected 2 videos, got {len(videos)}"
    assert all(isinstance(v, VideoSummary) for v in videos), "expected all items to be VideoSummary instances"


def test_should_contain_video_summary_for_video_1(repository_with_data):
    videos = repository_with_data.list_videos()
    video_1 = next((v for v in videos if v.video_id == "video-1"), None)
    
    assert video_1 is not None, "expected to find video-1 in results"
    assert video_1.word_count == 10, f"expected word_count 10, got {video_1.word_count}"
    assert video_1.extra == {"foo": "bar"}, f"expected extra {{'foo': 'bar'}}, got {video_1.extra}"


def test_should_contain_video_summary_for_video_2(repository_with_data):
    videos = repository_with_data.list_videos()
    video_2 = next((v for v in videos if v.video_id == "video-2"), None)
    
    assert video_2 is not None, "expected to find video-2 in results"
    assert video_2.word_count == 20, f"expected word_count 20, got {video_2.word_count}"
    assert video_2.extra == {"foo": "baz"}, f"expected extra {{'foo': 'baz'}}, got {video_2.extra}"


def test_should_return_empty_list_when_no_documents(mongo_client):
    repository = MongoReportRepository(mongo_client)
    videos = repository.list_videos()
    
    assert videos == [], f"expected empty list, got {videos}"


def test_should_return_video_summary_when_video_exists(repository_with_data):
    video = repository_with_data.get_video("video-1")
    
    assert video is not None, "expected video to be found"
    assert video.video_id == "video-1"
    assert video.word_count == 10
    assert video.extra == {"foo": "bar"}


def test_should_return_none_when_video_does_not_exist(repository_with_data):
    video = repository_with_data.get_video("missing-video")
    
    assert video is None, f"expected None, got {video}"
