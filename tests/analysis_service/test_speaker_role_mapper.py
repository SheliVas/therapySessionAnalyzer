import hashlib
import json
from typing import Any

import pytest

from src.analysis_service.speaker_role_mapper import map_speakers_to_roles
from tests.analysis_service.conftest import FakeRedisCache, FakeLLMClient


def _expected_cache_key(utterances: list[dict[str, Any]], prompt_id: str) -> str:
    payload = {"prompt_id": prompt_id, "utterances": utterances}
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    return f"speaker_role_mapping:{digest}"


# --- Fixtures ---


@pytest.fixture
def prompt_id() -> str:
    return "speaker-role-mapping-v1"


# --- Unit Tests ---


@pytest.mark.unit
def test_should_return_mapping_when_llm_returns_valid_json(
    utterances_two_speakers: list[dict[str, Any]],
    prompt_id: str,
    fake_llm_client: FakeLLMClient,
    fake_redis: FakeRedisCache,
):
    llm_result = {
        "speaker_roles": {
            "A": {"role": "patient", "confidence": 0.86, "reason": "Shares problems and feelings."},
            "B": {"role": "therapist", "confidence": 0.91, "reason": "Asks guiding questions."},
        },
        "overall_confidence": 0.9,
    }
    fake_llm_client.return_value = llm_result

    result = map_speakers_to_roles(
        utterances=utterances_two_speakers,
        llm_client=fake_llm_client,
        cache=fake_redis,
        prompt_id=prompt_id,
        ttl_seconds=300,
    )

    assert result == llm_result


@pytest.mark.unit
def test_should_skip_llm_call_when_cache_hit(
    utterances_two_speakers: list[dict[str, Any]],
    prompt_id: str,
    fake_llm_client: FakeLLMClient,
    fake_redis: FakeRedisCache,
):
    cached = {
        "speaker_roles": {
            "A": {"role": "therapist", "confidence": 0.8, "reason": "Guides conversation."},
            "B": {"role": "patient", "confidence": 0.8, "reason": "Shares experiences."},
        },
        "overall_confidence": 0.8,
    }
    fake_llm_client.return_value = {"unexpected": True}

    expected_key = _expected_cache_key(utterances_two_speakers, prompt_id)
    fake_redis.cache[expected_key] = cached

    result = map_speakers_to_roles(
        utterances=utterances_two_speakers,
        llm_client=fake_llm_client,
        cache=fake_redis,
        prompt_id=prompt_id,
        ttl_seconds=300,
    )

    assert fake_redis.last_get_key == expected_key
    assert fake_llm_client.call_count == 0
    assert result == cached


@pytest.mark.unit
@pytest.mark.parametrize(
    "utterances",
    [
        ([{"speaker_label": "A", "text": "Only one speaker."}]),
        (
            [
                {"speaker_label": "A", "text": "One"},
                {"speaker_label": "B", "text": "Two"},
                {"speaker_label": "C", "text": "Three"},
            ]
        ),
    ],
)
def test_should_raise_value_error_when_not_exactly_two_speakers(
    utterances: list[dict[str, Any]],
    prompt_id: str,
    fake_llm_client: FakeLLMClient,
    fake_redis: FakeRedisCache,
):
    fake_llm_client.return_value = {}

    with pytest.raises(ValueError):
        map_speakers_to_roles(
            utterances=utterances,
            llm_client=fake_llm_client,
            cache=fake_redis,
            prompt_id=prompt_id,
            ttl_seconds=300,
        )
