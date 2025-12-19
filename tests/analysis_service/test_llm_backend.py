import pytest
from src.analysis_service.llm_backend import LLMAnalysisBackend
from tests.analysis_service.conftest import FakeRedisCache, FakeLLMClient


# --- Fixtures ---

@pytest.fixture
def backend(fake_redis: FakeRedisCache, fake_llm_client: FakeLLMClient, cache_ttl: int) -> LLMAnalysisBackend:
    return LLMAnalysisBackend(
        llm_client=fake_llm_client,
        redis_cache=fake_redis,
        cache_ttl_seconds=cache_ttl
    )


# --- Unit Tests ---

@pytest.mark.unit
def test_should_call_llm_on_cache_miss_and_skip_on_cache_hit(
    backend: LLMAnalysisBackend,
    fake_redis: FakeRedisCache,
    fake_llm_client: FakeLLMClient,
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
def test_should_include_word_count_in_result(
    backend: LLMAnalysisBackend,
    sample_transcript: str,
) -> None:
    """word_count in AnalysisResult should match full transcript word count."""
    result = backend.analyze(sample_transcript)
    
    expected_word_count = len(sample_transcript.split())
    assert result.word_count == expected_word_count


@pytest.mark.unit
def test_should_include_backend_llm_in_extra(
    backend: LLMAnalysisBackend,
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
    backend: LLMAnalysisBackend,
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
    backend: LLMAnalysisBackend,
    sample_transcript: str,
) -> None:
    """Chunks and emotion_timeline lengths should match the number of chunks."""
    result = backend.analyze(sample_transcript)
    chunks = backend._split_transcript(sample_transcript)
    
    assert len(result.extra["chunks"]) == len(chunks)
    assert len(result.extra["emotion_timeline"]) == len(chunks)


@pytest.mark.unit
def test_emotion_timeline_entries_have_emotion_and_timestamp(
    backend: LLMAnalysisBackend,
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
    backend: LLMAnalysisBackend,
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
    backend: LLMAnalysisBackend,
    transcript: str,
    expected_word_count: int,
) -> None:
    """Word count should be calculated correctly."""
    result = backend.analyze(transcript)
    
    assert result.word_count == expected_word_count
