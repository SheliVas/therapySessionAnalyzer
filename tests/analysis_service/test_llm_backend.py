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
    # Mock transcript with Speaker labels to trigger parsing
    transcript = "Speaker A: Hello\nSpeaker B: Hi"
    
    # Mock LLM responses for speaker mapping and utterance tagging
    fake_llm_client.side_effect = [
        # Speaker mapping
        {
            "speaker_roles": {
                "Speaker A": {"role": "therapist", "confidence": 0.9, "reason": "test"},
                "Speaker B": {"role": "patient", "confidence": 0.9, "reason": "test"}
            },
            "overall_confidence": 0.9
        },
        # Utterance tagging
        {
            "utterances": [
                {"topic": "greeting", "emotion": "neutral"},
                {"topic": "greeting", "emotion": "neutral"}
            ]
        },
        # Recommendations
        {
            "therapist_recommendations": [
                {"title": "Rec 1", "rationale": "Rationale 1", "priority": "high", "related_topics": ["greeting"], "target_emotions": ["neutral"]},
                {"title": "Rec 2", "rationale": "Rationale 2", "priority": "medium", "related_topics": ["greeting"], "target_emotions": ["neutral"]},
                {"title": "Rec 3", "rationale": "Rationale 3", "priority": "low", "related_topics": [], "target_emotions": []}
            ]
        }
    ]

    result1 = backend.analyze(transcript, video_id="v1")
    first_call_count = fake_llm_client.call_count
    assert first_call_count == 3 # One for mapping, one for tagging, one for recommendations
    
    assert len(fake_redis.cache) > 0
    for key, ttl in fake_redis.ttls.items():
        assert ttl == cache_ttl
    
    fake_llm_client.call_count = 0
    result2 = backend.analyze(transcript, video_id="v1")
    second_call_count = fake_llm_client.call_count
    
    assert second_call_count == 0


@pytest.mark.unit
def test_should_include_word_count_in_result(
    backend: LLMAnalysisBackend,
    fake_llm_client: FakeLLMClient,
) -> None:
    """word_count in AnalysisResult should match full transcript word count."""
    transcript = "Speaker A: Hello\nSpeaker B: Hi"
    fake_llm_client.side_effect = [
        {"speaker_roles": {"Speaker A": {"role": "therapist", "confidence": 0.9, "reason": "test"}, "Speaker B": {"role": "patient", "confidence": 0.9, "reason": "test"}}, "overall_confidence": 0.9},
        {"utterances": [{"topic": "greeting", "emotion": "neutral"}, {"topic": "greeting", "emotion": "neutral"}]},
        {"therapist_recommendations": [{"title": "t", "rationale": "r", "priority": "high", "related_topics": [], "target_emotions": []}] * 3}
    ]
    result = backend.analyze(transcript, video_id="v1")
    
    expected_word_count = len(transcript.split())
    assert result.word_count == expected_word_count


@pytest.mark.unit
def test_should_include_utterances_in_extra(
    backend: LLMAnalysisBackend,
    fake_llm_client: FakeLLMClient,
) -> None:
    """extra should contain utterances."""
    transcript = "Speaker A: Hello\nSpeaker B: Hi"
    fake_llm_client.side_effect = [
        {"speaker_roles": {"Speaker A": {"role": "therapist", "confidence": 0.9, "reason": "test"}, "Speaker B": {"role": "patient", "confidence": 0.9, "reason": "test"}}, "overall_confidence": 0.9},
        {"utterances": [{"topic": "greeting", "emotion": "neutral"}, {"topic": "greeting", "emotion": "neutral"}]},
        {"therapist_recommendations": [{"title": "t", "rationale": "r", "priority": "high", "related_topics": [], "target_emotions": []}] * 3}
    ]
    result = backend.analyze(transcript, video_id="v1")
    
    assert "utterances" in result.extra
    assert len(result.extra["utterances"]) == 2


@pytest.mark.unit
def test_extra_contains_utterances(
    backend: LLMAnalysisBackend,
    fake_llm_client: FakeLLMClient,
) -> None:
    """extra dict should contain utterances."""
    transcript = "Speaker A: Hello\nSpeaker B: Hi"
    fake_llm_client.side_effect = [
        {"speaker_roles": {"Speaker A": {"role": "therapist", "confidence": 0.9, "reason": "test"}, "Speaker B": {"role": "patient", "confidence": 0.9, "reason": "test"}}, "overall_confidence": 0.9},
        {"utterances": [{"topic": "greeting", "emotion": "neutral"}, {"topic": "greeting", "emotion": "neutral"}]},
        {"therapist_recommendations": [{"title": "t", "rationale": "r", "priority": "high", "related_topics": [], "target_emotions": []}] * 3}
    ]
    result = backend.analyze(transcript, video_id="v1")
    
    assert "utterances" in result.extra
    assert isinstance(result.extra["utterances"], list)
    assert len(result.extra["utterances"]) == 2


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
    fake_llm_client: FakeLLMClient,
) -> None:
    """Word count should be calculated correctly."""
    # Need to mock side effects because analyze calls LLM
    fake_llm_client.side_effect = [
        {"speaker_roles": {}, "overall_confidence": 0.0}, # Mapping
        {"utterances": []}, # Tagging
        {"therapist_recommendations": [{"title": "t", "rationale": "r", "priority": "high", "related_topics": [], "target_emotions": []}] * 3} # Recs
    ] * 3 # Repeat for each param case if needed, but actually parametrize runs separate tests.
    # Wait, parametrize runs the test function multiple times.
    # So side_effect needs to be set for each run.
    
    # However, if transcript is empty or no speakers, parse_transcript returns empty list.
    # And analyze returns early.
    # So LLM might not be called.
    
    result = backend.analyze(transcript, video_id="v1")
    
    assert result.word_count == expected_word_count
