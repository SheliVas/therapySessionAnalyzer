import pytest
from pathlib import Path
from typing import Dict, Any, Protocol, List, Optional
from src.transcription_service.domain import TranscriptCreatedEvent
from src.analysis_service.domain import AnalysisBackend, AnalysisResult
from src.analysis_service.llm_client import LLMClient
from src.analysis_service.redis_cache import RedisCache
from src.analysis_service.worker import (
    AnalysisCompletedEvent,
    AnalysisEventPublisher,
    AnalysisRepository,
)


class StorageClient(Protocol):
    def download_file(self, bucket: str, key: str) -> bytes:
        ...

    def upload_file(self, bucket: str, key: str, content: bytes) -> None:
        ...


class FakeStorageClient:
    def __init__(self) -> None:
        self.files: Dict[str, bytes] = {}
        self.upload_calls: list[tuple[str, str, bytes]] = []

    def download_file(self, bucket: str, key: str) -> bytes:
        path = f"{bucket}/{key}"
        return self.files.get(path, b"")

    def upload_file(self, bucket: str, key: str, content: bytes) -> None:
        path = f"{bucket}/{key}"
        self.files[path] = content
        self.upload_calls.append((bucket, key, content))

    def add_file(self, bucket: str, key: str, content: bytes) -> None:
        path = f"{bucket}/{key}"
        self.files[path] = content


class FakeAnalysisBackend(AnalysisBackend):
    def __init__(self, video_id: str = "video-123") -> None:
        self.video_id = video_id
        self.calls: list[str] = []

    def analyze(self, transcript_text: str) -> AnalysisResult:
        self.calls.append(transcript_text)
        word_count = len(transcript_text.split())
        return AnalysisResult(
            video_id=self.video_id,
            word_count=word_count,
            extra={"backend": "fake"}
        )


class FakeAnalysisEventPublisher(AnalysisEventPublisher):
    def __init__(self) -> None:
        self.published_events: list[AnalysisCompletedEvent] = []

    def publish_analysis_completed(self, event: AnalysisCompletedEvent) -> None:
        self.published_events.append(event)


class FakeAnalysisRepository(AnalysisRepository):
    def __init__(self) -> None:
        self.saved_events: list[AnalysisCompletedEvent] = []

    def save_analysis(self, event: AnalysisCompletedEvent) -> None:
        self.saved_events.append(event)


class FakeRedisCache(RedisCache):
    """Unified Fake Redis cache for testing."""
    def __init__(self) -> None:
        self.cache: Dict[str, Any] = {}
        self.ttls: Dict[str, int] = {}
        self.last_get_key: Optional[str] = None
        self.last_set: Optional[tuple[str, Any, int]] = None
    
    def get(self, key: str) -> Optional[Any]:
        self.last_get_key = key
        return self.cache.get(key)
    
    def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        self.cache[key] = value
        self.ttls[key] = ttl_seconds
        self.last_set = (key, value, ttl_seconds)


class FakeLLMClient(LLMClient):
    """Fake LLM client for testing."""
    def __init__(self, return_value: Dict[str, Any]) -> None:
        self.return_value = return_value
        self.call_count = 0
        self.call_args: List[str] = []
        self.last_prompt: Optional[str] = None

    def analyze_transcript(self, transcript_text: str) -> Dict[str, Any]:
        self.call_count += 1
        self.call_args.append(transcript_text)
        self.last_prompt = transcript_text
        return self.return_value


@pytest.fixture
def video_id() -> str:
    return "video-123"


@pytest.fixture
def event(video_id: str) -> TranscriptCreatedEvent:
    return TranscriptCreatedEvent(
        video_id=video_id,
        bucket="therapy-transcripts",
        key=f"transcripts/{video_id}/transcript.txt",
    )


@pytest.fixture
def fake_storage_client(event: TranscriptCreatedEvent) -> FakeStorageClient:
    client = FakeStorageClient()
    client.add_file(event.bucket, event.key, b"hello world hello")
    return client


@pytest.fixture
def fake_backend(video_id: str) -> FakeAnalysisBackend:
    return FakeAnalysisBackend(video_id=video_id)


@pytest.fixture
def fake_publisher() -> FakeAnalysisEventPublisher:
    return FakeAnalysisEventPublisher()


@pytest.fixture
def fake_repository() -> FakeAnalysisRepository:
    return FakeAnalysisRepository()


@pytest.fixture
def fake_llm_result() -> Dict[str, Any]:
    return {"emotion": "neutral", "topic": "work"}


@pytest.fixture
def fake_llm_client(fake_llm_result: Dict[str, Any]) -> FakeLLMClient:
    return FakeLLMClient(return_value=fake_llm_result)


@pytest.fixture
def fake_redis() -> FakeRedisCache:
    return FakeRedisCache()


@pytest.fixture
def utterances_two_speakers() -> List[Dict[str, str]]:
    return [
        {"speaker_label": "A", "text": "Hi, thanks for meeting today."},
        {"speaker_label": "B", "text": "Of course. What feels most important?"},
        {"speaker_label": "A", "text": "I have been anxious at work."},
        {"speaker_label": "B", "text": "When did you first notice that anxiety?"},
        {"speaker_label": "A", "text": "A few months ago after a reorg."},
        {"speaker_label": "B", "text": "Let’s explore the thoughts that come up."},
    ]


@pytest.fixture
def speaker_labels() -> List[str]:
    return ["A", "B"]


@pytest.fixture
def sample_transcript() -> str:
    return """The client arrived on time.
They discussed their recent work stress.
We explored coping mechanisms.

The client felt heard and validated.
They left feeling more hopeful."""


@pytest.fixture
def cache_ttl() -> int:
    return 3600  # 1 hour

