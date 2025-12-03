import pytest


# --- Unit Tests ---


@pytest.mark.unit
def test_should_return_200_when_videos_endpoint_called(client):
    response = client.get("/videos")
    
    assert response.status_code == 200, f"expected status code 200, got {response.status_code}"


@pytest.mark.unit
def test_should_return_videos_list_as_json(client, sample_videos):
    response = client.get("/videos")
    data = response.json()
    
    assert isinstance(data, list), f"expected list, got {type(data)}"
    assert len(data) == 2, f"expected 2 videos, got {len(data)}"


@pytest.mark.unit
@pytest.mark.parametrize("video_id,expected_word_count,expected_extra", [
    ("video-1", 10, {"foo": "bar"}),
    ("video-2", 20, {"foo": "baz"}),
])
def test_should_return_video_data(client, sample_videos, video_id, expected_word_count, expected_extra):

    response = client.get("/videos")
    data = response.json()
    

    video = next((v for v in data if v["video_id"] == video_id), None)
    assert video is not None, f"expected to find {video_id} in results"
    assert video["word_count"] == expected_word_count, f"expected word_count {expected_word_count}, got {video['word_count']}"
    assert video["extra"] == expected_extra, f"expected extra {expected_extra}, got {video['extra']}"
