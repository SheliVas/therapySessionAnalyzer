def test_should_return_200_when_videos_endpoint_called(client):
    response = client.get("/videos")
    
    assert response.status_code == 200, f"expected status code 200, got {response.status_code}"


def test_should_return_videos_list_as_json(client, sample_videos):
    response = client.get("/videos")
    data = response.json()
    
    assert isinstance(data, list), f"expected list, got {type(data)}"
    assert len(data) == 2, f"expected 2 videos, got {len(data)}"


def test_should_return_video_1_data(client, sample_videos):
    response = client.get("/videos")
    data = response.json()
    
    video_1 = next((v for v in data if v["video_id"] == "video-1"), None)
    assert video_1 is not None, "expected to find video-1 in results"
    assert video_1["word_count"] == 10, f"expected word_count 10, got {video_1['word_count']}"
    assert video_1["extra"] == {"foo": "bar"}, f"expected extra {{'foo': 'bar'}}, got {video_1['extra']}"


def test_should_return_video_2_data(client, sample_videos):
    response = client.get("/videos")
    data = response.json()
    
    video_2 = next((v for v in data if v["video_id"] == "video-2"), None)
    assert video_2 is not None, "expected to find video-2 in results"
    assert video_2["word_count"] == 20, f"expected word_count 20, got {video_2['word_count']}"
    assert video_2["extra"] == {"foo": "baz"}, f"expected extra {{'foo': 'baz'}}, got {video_2['extra']}"
