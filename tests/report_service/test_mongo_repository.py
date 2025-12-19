import pytest
from src.report_service.mongo_repository import VideoSummary, MongoReportRepository


@pytest.fixture
def sample_documents():
    return {
        "analysis": [
            {
                "video_id": "video-1",
                "word_count": 10,
                "extra": {
                    "foo": "bar",
                    "recommendations": [
                        {
                            "title": "Rec 1",
                            "rationale": "Rat 1",
                            "priority": "high",
                            "related_topics": ["topic1"],
                            "target_emotions": ["emotion1"]
                        }
                    ]
                }
            },
            {
                "video_id": "video-2",
                "word_count": 20,
                "extra": {
                    "foo": "baz",
                    "recommendations": [
                        {
                            "title": "Rec 2",
                            "rationale": "Rat 2",
                            "priority": "low",
                            "related_topics": ["topic2"],
                            "target_emotions": ["emotion2"]
                        }
                    ]
                }
            }
        ],
        "videos": [
            {
                "video_id": "video-1",
                "status": "analyzed"
            },
            {
                "video_id": "video-2",
                "status": "analyzed"
            },
            {
                "video_id": "video-3",
                "status": "uploaded"
            }
        ]
    }


@pytest.fixture
def repository_with_data(mongo_client, sample_documents):
    db = mongo_client["therapy_analysis"]
    db["analysis_results"].insert_many(sample_documents["analysis"])
    db["videos"].insert_many(sample_documents["videos"])
    return MongoReportRepository(mongo_client)


@pytest.mark.unit
def test_should_list_only_analyzed_videos(repository_with_data):
    videos = repository_with_data.list_videos()
    
    assert len(videos) == 2
    assert all(v.status == "analyzed" for v in videos)
    assert {v.video_id for v in videos} == {"video-1", "video-2"}


@pytest.mark.unit
@pytest.mark.parametrize("video_id, expected_word_count, expected_status, expected_extra", [
    ("video-1", 10, "analyzed", {
        "foo": "bar",
        "recommendations": [
            {
                "title": "Rec 1",
                "rationale": "Rat 1",
                "priority": "high",
                "related_topics": ["topic1"],
                "target_emotions": ["emotion1"]
            }
        ]
    }),
    ("video-2", 20, "analyzed", {
        "foo": "baz",
        "recommendations": [
            {
                "title": "Rec 2",
                "rationale": "Rat 2",
                "priority": "low",
                "related_topics": ["topic2"],
                "target_emotions": ["emotion2"]
            }
        ]
    }),
])
def test_should_contain_correct_video_summaries(
    repository_with_data, 
    video_id, 
    expected_word_count, 
    expected_status,
    expected_extra
):
    videos = repository_with_data.list_videos()
    video = next((v for v in videos if v.video_id == video_id), None)
    
    assert video is not None
    assert video.word_count == expected_word_count
    assert video.status == expected_status
    assert video.extra == expected_extra


@pytest.mark.unit
def test_should_return_empty_list_when_no_documents(mongo_client):
    repository = MongoReportRepository(mongo_client)
    videos = repository.list_videos()
    
    assert videos == []


@pytest.mark.unit
def test_should_return_video_summary_when_video_exists(repository_with_data):
    video = repository_with_data.get_video("video-1")
    
    assert video is not None
    assert video.video_id == "video-1"
    assert video.word_count == 10
    assert video.status == "analyzed"
    assert video.extra["foo"] == "bar"
    assert "recommendations" in video.extra


@pytest.mark.unit
def test_should_return_none_when_video_does_not_exist(repository_with_data):
    video = repository_with_data.get_video("missing-video")
    
    assert video is None


@pytest.mark.unit
def test_should_return_recommendations_in_extra(repository_with_data):
    video = repository_with_data.get_video("video-1")
    
    assert video is not None
    assert "recommendations" in video.extra
    assert len(video.extra["recommendations"]) == 1
    assert video.extra["recommendations"][0]["title"] == "Rec 1"
    assert video.extra["recommendations"][0]["priority"] == "high"
