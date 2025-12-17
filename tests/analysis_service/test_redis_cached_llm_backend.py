import pytest
from typing import Dict, Any, Optional
from unittest.mock import MagicMock
from src.analysis_service.redis_cache import RedisCache
from src.analysis_service.cached_llm_backend import CachedLLMAnalysisBackend
from src.analysis_service.domain import AnalysisResult
from src.analysis_service.llm_client import LLMClient


# --- Fakes ---

class FakeRedisCache(RedisCache):
    """Fake Redis cache for testing."""
    def __init__(self) -> None:
        self.cache: Dict[str, Any] = {}
        self.ttls: Dict[str, int] = {}
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        return self.cache.get(key)
    
    def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        """Set value in cache with TTL."""
        self.cache[key] = value
        self.ttls[key] = ttl_seconds


class FakeLLMClientWithCallTracking(LLMClient):
    """Fake LLM client that tracks calls."""
    def __init__(self, return_value: Dict[str, Any]) -> None:
        self.return_value = return_value
        self.call_count = 0
        self.call_args: list[str] = []
    
    def analyze_transcript(self, transcript_text: str) -> Dict[str, Any]:
        """Analyze and track calls."""
        self.call_count += 1
        self.call_args.append(transcript_text)
        return self.return_value


# --- Fixtures ---

@pytest.fixture
def fake_redis() -> FakeRedisCache:
    return FakeRedisCache()


@pytest.fixture
def fake_llm_client() -> FakeLLMClientWithCallTracking:
    return FakeLLMClientWithCallTracking(
        return_value={"emotion": "calm", "summary": "client discussing work stress"}
    )


@pytest.fixture
def cache_ttl() -> int:
    return 3600  # 1 hour


@pytest.fixture
def backend(fake_redis: FakeRedisCache, fake_llm_client: FakeLLMClientWithCallTracking, cache_ttl: int) -> CachedLLMAnalysisBackend:
    return CachedLLMAnalysisBackend(
        llm_client=fake_llm_client,
        redis_cache=fake_redis,
        cache_ttl_seconds=cache_ttl
    )


@pytest.fixture
def sample_transcript() -> str:
    return """The client arrived on time.
They discussed their recent work stress.
We explored coping mechanisms.

The client felt heard and validated.
They left feeling more hopeful."""


# --- Unit Tests ---

@pytest.mark.unit
def test_should_call_llm_on_cache_miss_and_skip_on_cache_hit(
    backend: CachedLLMAnalysisBackend,
    fake_redis: FakeRedisCache,
    fake_llm_client: FakeLLMClientWithCallTracking,
    sample_transcript: str,
    cache_ttl: int,
) -> None:
    """
    First call: cache misses trigger LLM calls and store results with TTL.
    Second call: cache hits skip LLM calls entirely.
    """
    result1 = backend.analyze(sample_transcript)
    first_call_count = fake_llm_client.call_count
    assert first_call_count > 0
    
    assert len(fake_redis.cache) > 0
    for key, ttl in fake_redis.ttls.items():
        assert ttl == cache_ttl
    
    fake_llm_client.call_count = 0
    result2 = backend.analyze(sample_transcript)
    second_call_count = fake_llm_client.call_count
    
    assert second_call_count == 0


@pytest.mark.unit
@pytest.mark.parametrize(
    "chunk1,chunk2,prompt1,prompt2,should_be_equal",
    [
        ("stress text", "stress text", "v1", "v1", True),
        ("chunk1", "chunk2", "v1", "v1", False),
        ("stress text", "stress text", "v1", "v2", False),
    ]
)
def test_cache_key_determinism_and_uniqueness(
    backend: CachedLLMAnalysisBackend,
    chunk1: str,
    chunk2: str,
    prompt1: str,
    prompt2: str,
    should_be_equal: bool,
) -> None:
    """Cache keys should be deterministic and unique based on chunk and prompt_id."""
    key1 = backend._build_cache_key(chunk1, prompt_id=prompt1)
    key2 = backend._build_cache_key(chunk2, prompt_id=prompt2)
    
    if should_be_equal:
        assert key1 == key2
    else:
        assert key1 != key2


@pytest.mark.unit
def test_should_include_word_count_in_result(
    backend: CachedLLMAnalysisBackend,
    sample_transcript: str,
) -> None:
    """word_count in AnalysisResult should match full transcript word count."""
    result = backend.analyze(sample_transcript)
    
    expected_word_count = len(sample_transcript.split())
    assert result.word_count == expected_word_count


@pytest.mark.unit
def test_should_include_backend_llm_in_extra(
    backend: CachedLLMAnalysisBackend,
    sample_transcript: str,
) -> None:
    """extra should contain backend="llm"."""
    result = backend.analyze(sample_transcript)
    
    assert result.extra["backend"] == "llm"


@pytest.mark.unit
@pytest.mark.parametrize(
    "extra_key,expected_type",
    [
        ("chunks", list),
        ("emotion_timeline", list),
    ]
)
def test_extra_contains_required_keys_with_correct_types(
    backend: CachedLLMAnalysisBackend,
    sample_transcript: str,
    extra_key: str,
    expected_type: type,
) -> None:
    """extra dict should contain required keys with correct types."""
    result = backend.analyze(sample_transcript)
    
    assert extra_key in result.extra
    assert isinstance(result.extra[extra_key], expected_type)
    assert len(result.extra[extra_key]) > 0


@pytest.mark.unit
def test_chunks_and_emotion_timeline_lengths_match_chunk_count(
    backend: CachedLLMAnalysisBackend,
    sample_transcript: str,
) -> None:
    """Chunks and emotion_timeline lengths should match the number of chunks."""
    result = backend.analyze(sample_transcript)
    chunks = backend._split_transcript(sample_transcript)
    
    assert len(result.extra["chunks"]) == len(chunks)
    assert len(result.extra["emotion_timeline"]) == len(chunks)


@pytest.mark.unit
def test_emotion_timeline_entries_have_emotion_and_timestamp(
    backend: CachedLLMAnalysisBackend,
    sample_transcript: str,
) -> None:
    """Each emotion_timeline entry should have emotion and chunk_index."""
    result = backend.analyze(sample_transcript)
    
    for entry in result.extra["emotion_timeline"]:
        assert "emotion" in entry
        assert "chunk_index" in entry


@pytest.mark.unit
@pytest.mark.parametrize(
    "transcript",
    [
        "Single line transcript.",
        "Line one.\nLine two.\nLine three.",
        """Multi-paragraph transcript.

Second paragraph here.

Third paragraph.""",
    ]
)
def test_should_split_transcript_into_non_empty_chunks(
    backend: CachedLLMAnalysisBackend,
    transcript: str,
) -> None:
    """Transcript should be split into non-empty chunks."""
    chunks = backend._split_transcript(transcript)
    
    assert isinstance(chunks, list)
    assert len(chunks) > 0
    for chunk in chunks:
        assert isinstance(chunk, str)
        assert len(chunk.strip()) > 0


@pytest.mark.unit
@pytest.mark.parametrize(
    "transcript,expected_word_count",
    [
        ("hello world hello", 3),
        ("", 0),
        ("   \n  \t ", 0),
    ]
)
def test_word_count_calculation(
    backend: CachedLLMAnalysisBackend,
    transcript: str,
    expected_word_count: int,
) -> None:
    """Word count should be calculated correctly."""
    result = backend.analyze(transcript)
    
    assert result.word_count == expected_word_count
