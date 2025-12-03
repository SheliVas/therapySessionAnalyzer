import pytest


# --- Unit Tests ---


@pytest.mark.unit
def test_should_return_200_when_videos_endpoint_called(client):
    response = client.get("/videos")
    
    assert response.status_code == 200


@pytest.mark.unit
def test_should_return_videos_list_as_json(client, sample_videos):
    response = client.get("/videos")
    data = response.json()
    
    assert isinstance(data, list)
    assert len(data) == 2


@pytest.mark.unit
@pytest.mark.parametrize("video_id,expected_word_count,expected_extra", [
    ("video-1", 10, {"foo": "bar"}),
    ("video-2", 20, {"foo": "baz"}),
])
def test_should_return_video_data(client, sample_videos, video_id, expected_word_count, expected_extra):

    response = client.get("/videos")
    data = response.json()
    

    video = next((v for v in data if v["video_id"] == video_id), None)
    assert video is not None
    assert video["word_count"] == expected_word_count
    assert video["extra"] == expected_extra
