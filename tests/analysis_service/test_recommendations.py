import pytest
from typing import Any
from src.analysis_service.recommendations import generate_therapist_recommendations

@pytest.fixture
def sample_utterances():
    return [
        {"index": 0, "speaker_label": "T", "role": "therapist", "text": "Hello", "topic": "intro", "emotion": "neutral"},
        {"index": 1, "speaker_label": "P", "role": "patient", "text": "Hi", "topic": "intro", "emotion": "sad"},
    ]

@pytest.fixture
def valid_recommendations():
    return {
        "therapist_recommendations": [
            {
                "title": "Rec 1",
                "rationale": "Rationale 1",
                "priority": "high",
                "related_topics": ["intro"],
                "target_emotions": ["sad"]
            },
            {
                "title": "Rec 2",
                "rationale": "Rationale 2",
                "priority": "medium",
                "related_topics": ["intro"],
                "target_emotions": ["neutral"]
            },
            {
                "title": "Rec 3",
                "rationale": "Rationale 3",
                "priority": "low",
                "related_topics": [],
                "target_emotions": []
            }
        ]
    }

@pytest.mark.unit
def test_cache_miss_calls_llm_and_sets_cache(fake_llm_client, fake_redis, sample_utterances, valid_recommendations):
    fake_llm_client.return_value = valid_recommendations
    
    result = generate_therapist_recommendations(
        video_id="vid1",
        utterances=sample_utterances,
        llm_client=fake_llm_client,
        cache=fake_redis,
        prompt_id="p1",
        ttl_seconds=60
    )
    
    assert result == valid_recommendations
    assert fake_llm_client.call_count == 1
    assert fake_redis.last_set is not None
    assert fake_redis.last_set[2] == 60 # TTL

@pytest.mark.unit
def test_cache_hit_returns_cached_result(fake_llm_client, fake_redis, sample_utterances, valid_recommendations):
    fake_llm_client.return_value = valid_recommendations
    
    # First run (miss) - populates cache
    generate_therapist_recommendations(
        video_id="vid1",
        utterances=sample_utterances,
        llm_client=fake_llm_client,
        cache=fake_redis,
        prompt_id="p1",
        ttl_seconds=60
    )
    
    # Reset LLM calls
    fake_llm_client.call_count = 0
    
    # Second run (hit)
    result = generate_therapist_recommendations(
        video_id="vid1",
        utterances=sample_utterances,
        llm_client=fake_llm_client,
        cache=fake_redis,
        prompt_id="p1",
        ttl_seconds=60
    )
    
    assert result == valid_recommendations
    assert fake_llm_client.call_count == 0

@pytest.mark.unit
@pytest.mark.parametrize("invalid_output, error_match", [
    ({"therapist_recommendations": [{"title": "t", "rationale": "r", "priority": "invalid", "related_topics": [], "target_emotions": []}] * 3}, "priority"),
    ({"therapist_recommendations": [{"title": "t", "rationale": "r", "priority": "high", "related_topics": ["unknown"], "target_emotions": []}] * 3}, "related_topics"),
    ({"therapist_recommendations": [{"title": "t", "rationale": "r", "priority": "high", "related_topics": [], "target_emotions": ["unknown"]}] * 3}, "target_emotions"),
    ({"therapist_recommendations": [{"title": "t", "rationale": "r", "priority": "high", "related_topics": [], "target_emotions": [], "extra": "field"}] * 3}, "extra keys"),
    ({"other_key": "val"}, "output keys"),
])
def test_invalid_outputs_raise_value_error(fake_llm_client, fake_redis, sample_utterances, invalid_output, error_match):
    fake_llm_client.return_value = invalid_output
    
    with pytest.raises(ValueError, match=error_match):
        generate_therapist_recommendations(
            video_id="vid1",
            utterances=sample_utterances,
            llm_client=fake_llm_client,
            cache=fake_redis,
            prompt_id="p1",
            ttl_seconds=60
        )
