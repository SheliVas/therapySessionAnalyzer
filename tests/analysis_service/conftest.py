import pytest
from pathlib import Path
from typing import Dict, Any, Protocol
from src.transcription_service.domain import TranscriptCreatedEvent
from src.analysis_service.domain import AnalysisBackend, AnalysisResult
from src.analysis_service.llm_client import LLMClient
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


class FakeLLMClient(LLMClient):
    """Fake LLM client for testing."""
    def __init__(self, return_value: Dict[str, Any]) -> None:
        self.return_value = return_value

    def analyze_transcript(self, transcript_text: str) -> Dict[str, Any]:
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
    return {"summary": "short summary", "topics": ["topic1", "topic2"]}


@pytest.fixture
def fake_llm_client(fake_llm_result: Dict[str, Any]) -> FakeLLMClient:
    return FakeLLMClient(return_value=fake_llm_result)
