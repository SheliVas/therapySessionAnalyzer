import pytest


@pytest.fixture
def fake_publisher(fake_video_publisher):
    """Alias the global fake_video_publisher fixture."""
    return fake_video_publisher
