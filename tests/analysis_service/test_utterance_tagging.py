import pytest
from unittest.mock import MagicMock
from src.analysis_service.domain import AnalysisResult
from src.analysis_service.llm_backend import LLMAnalysisBackend

# --- Fixtures ---

@pytest.fixture
def mock_llm_client():
    return MagicMock()

@pytest.fixture
def mock_redis_cache():
    cache = MagicMock()
    cache.get.return_value = None
    return cache

@pytest.fixture
def backend(mock_llm_client, mock_redis_cache):
    return LLMAnalysisBackend(
        llm_client=mock_llm_client,
        redis_cache=mock_redis_cache,
        prompt_id="test-prompt"
    )

@pytest.fixture
def sample_transcript():
    return (
        "Speaker A: Hello, how are you today?\n"
        "Speaker B: I'm feeling a bit anxious.\n"
        "Speaker A: I understand. What's on your mind?"
    )

# --- Unit Tests ---

@pytest.mark.unit
def test_should_parse_transcript_into_utterances_with_roles_topics_and_emotions(
    backend, mock_llm_client, sample_transcript
):
    mock_llm_client.analyze_transcript.side_effect = [
        # First call: speaker role mapping
        {
            "speaker_roles": {
                "Speaker A": {"role": "therapist", "confidence": 0.9, "reason": "test"},
                "Speaker B": {"role": "patient", "confidence": 0.9, "reason": "test"}
            },
            "overall_confidence": 0.9
        },
        # Second call: utterance tagging
        {
            "utterances": [
                {"topic": "greeting", "emotion": "neutral"},
                {"topic": "feelings", "emotion": "anxious"},
                {"topic": "exploration", "emotion": "empathetic"}
            ]
        },
        # Third call: recommendations
        {
            "therapist_recommendations": [
                {"title": "Rec 1", "rationale": "Rationale 1", "priority": "high", "related_topics": ["greeting"], "target_emotions": ["neutral"]},
                {"title": "Rec 2", "rationale": "Rationale 2", "priority": "medium", "related_topics": ["greeting"], "target_emotions": ["neutral"]},
                {"title": "Rec 3", "rationale": "Rationale 3", "priority": "low", "related_topics": [], "target_emotions": []}
            ]
        }
    ]

    result = backend.analyze(sample_transcript, video_id="v1")

    assert "tagging" in result.analysis
    assert "utterances" in result.analysis["tagging"]
    utterances = result.analysis["tagging"]["utterances"]
    assert len(utterances) == 3
    
    assert utterances[0] == {
        "index": 0,
        "speaker_label": "Speaker A",
        "role": "therapist",
        "text": "Hello, how are you today?",
        "topic": "greeting",
        "emotion": "neutral"
    }
    assert utterances[1] == {
        "index": 1,
        "speaker_label": "Speaker B",
        "role": "patient",
        "text": "I'm feeling a bit anxious.",
        "topic": "feelings",
        "emotion": "anxious"
    }
    assert utterances[2] == {
        "index": 2,
        "speaker_label": "Speaker A",
        "role": "therapist",
        "text": "I understand. What's on your mind?",
        "topic": "exploration",
        "emotion": "empathetic"
    }

@pytest.mark.unit
def test_should_use_cache_for_utterance_tagging(
    backend, mock_llm_client, mock_redis_cache, sample_transcript
):
    mock_llm_client.analyze_transcript.side_effect = [
        {
            "speaker_roles": {
                "Speaker A": {"role": "therapist", "confidence": 0.9, "reason": "test"},
                "Speaker B": {"role": "patient", "confidence": 0.9, "reason": "test"}
            },
            "overall_confidence": 0.9
        },
        {
            "therapist_recommendations": [
                {"title": "Rec 1", "rationale": "Rationale 1", "priority": "high", "related_topics": ["greeting"], "target_emotions": ["neutral"]},
                {"title": "Rec 2", "rationale": "Rationale 2", "priority": "medium", "related_topics": ["greeting"], "target_emotions": ["neutral"]},
                {"title": "Rec 3", "rationale": "Rationale 3", "priority": "low", "related_topics": [], "target_emotions": []}
            ]
        }
    ]
    
    mock_redis_cache.get.side_effect = [
        None, # Cache miss for speaker role mapping
        {
            "utterances": [
                {"topic": "greeting", "emotion": "neutral"},
                {"topic": "feelings", "emotion": "anxious"},
                {"topic": "exploration", "emotion": "empathetic"}
            ]
        }, # Cache hit for utterance tagging
        None # Cache miss for recommendations
    ]

    result = backend.analyze(sample_transcript, video_id="v1")

    assert len(result.analysis["tagging"]["utterances"]) == 3
    assert mock_llm_client.analyze_transcript.call_count == 2

@pytest.mark.unit
def test_should_raise_value_error_when_llm_returns_invalid_format(
    backend, mock_llm_client, sample_transcript
):
    mock_llm_client.analyze_transcript.side_effect = [
        {
            "speaker_roles": {
                "Speaker A": {"role": "therapist", "confidence": 0.9, "reason": "test"},
                "Speaker B": {"role": "patient", "confidence": 0.9, "reason": "test"}
            },
            "overall_confidence": 0.9
        },
        # Utterance tagging returns dict without 'utterances' key
        {"error": "something went wrong"}
    ]

    with pytest.raises(ValueError, match="LLM output must contain 'utterances' key"):
        backend.analyze(sample_transcript, video_id="v1")

@pytest.mark.unit
def test_should_handle_transcript_with_extra_whitespace_and_empty_lines(
    backend, mock_llm_client
):
    transcript = "\n\nSpeaker A: Hello\n\n\nSpeaker B: Hi\n   \n"
    mock_llm_client.analyze_transcript.side_effect = [
        {
            "speaker_roles": {
                "Speaker A": {"role": "therapist", "confidence": 0.9, "reason": "test"},
                "Speaker B": {"role": "patient", "confidence": 0.9, "reason": "test"}
            },
            "overall_confidence": 0.9
        },
        {
            "utterances": [
                {"topic": "greeting", "emotion": "neutral"},
                {"topic": "greeting", "emotion": "neutral"}
            ]
        },
        {
            "therapist_recommendations": [
                {"title": "Rec 1", "rationale": "Rationale 1", "priority": "high", "related_topics": ["greeting"], "target_emotions": ["neutral"]},
                {"title": "Rec 2", "rationale": "Rationale 2", "priority": "medium", "related_topics": ["greeting"], "target_emotions": ["neutral"]},
                {"title": "Rec 3", "rationale": "Rationale 3", "priority": "low", "related_topics": [], "target_emotions": []}
            ]
        }
    ]

    result = backend.analyze(transcript, video_id="v1")
    assert len(result.analysis["tagging"]["utterances"]) == 2
