import hashlib
import json
from typing import Any

import pytest

from src.analysis_service.speaker_role_mapper import map_speakers_to_roles


def _expected_cache_key(utterances: list[dict[str, Any]], prompt_id: str) -> str:
    payload = {"prompt_id": prompt_id, "utterances": utterances}
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    return f"speaker_role_mapping:{digest}"


# --- Fakes ---


class FakeRedisCache:
    def __init__(self):
        self._store: dict[str, Any] = {}
        self.last_get_key: str | None = None
        self.last_set: tuple[str, Any, int] | None = None

    def get(self, key: str):
        self.last_get_key = key
        return self._store.get(key)

    def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        self.last_set = (key, value, ttl_seconds)
        self._store[key] = value


class FakeLLMClient:
    def __init__(self, result: dict[str, Any]):
        self._result = result
        self.calls = 0
        self.last_prompt: str | None = None

    def analyze_transcript(self, transcript_text: str) -> dict[str, Any]:
        self.calls += 1
        self.last_prompt = transcript_text
        return self._result


# --- Fixtures ---


@pytest.fixture
def utterances_two_speakers() -> list[dict[str, Any]]:
    return [
        {"speaker_label": "A", "text": "Hi, thanks for meeting today."},
        {"speaker_label": "B", "text": "Of course. What feels most important?"},
        {"speaker_label": "A", "text": "I have been anxious at work."},
        {"speaker_label": "B", "text": "When did you first notice that anxiety?"},
        {"speaker_label": "A", "text": "A few months ago after a reorg."},
        {"speaker_label": "B", "text": "Let’s explore the thoughts that come up."},
    ]


@pytest.fixture
def prompt_id() -> str:
    return "speaker-role-mapping-v1"


# --- Unit Tests ---


@pytest.mark.unit
def test_should_return_mapping_when_llm_returns_valid_json(
    utterances_two_speakers: list[dict[str, Any]],
    prompt_id: str,
):
    llm_result = {
        "speaker_roles": {
            "A": {"role": "patient", "confidence": 0.86, "reason": "Shares problems and feelings."},
            "B": {"role": "therapist", "confidence": 0.91, "reason": "Asks guiding questions."},
        },
        "overall_confidence": 0.9,
    }
    llm = FakeLLMClient(result=llm_result)
    cache = FakeRedisCache()

    result = map_speakers_to_roles(
        utterances=utterances_two_speakers,
        llm_client=llm,
        cache=cache,
        prompt_id=prompt_id,
        ttl_seconds=300,
    )

    assert result == llm_result


@pytest.mark.unit
def test_should_skip_llm_call_when_cache_hit(
    utterances_two_speakers: list[dict[str, Any]],
    prompt_id: str,
):
    cached = {
        "speaker_roles": {
            "A": {"role": "therapist", "confidence": 0.8, "reason": "Guides conversation."},
            "B": {"role": "patient", "confidence": 0.8, "reason": "Shares experiences."},
        },
        "overall_confidence": 0.8,
    }
    llm = FakeLLMClient(result={"unexpected": True})
    cache = FakeRedisCache()

    expected_key = _expected_cache_key(utterances_two_speakers, prompt_id)
    cache._store[expected_key] = cached

    result = map_speakers_to_roles(
        utterances=utterances_two_speakers,
        llm_client=llm,
        cache=cache,
        prompt_id=prompt_id,
        ttl_seconds=300,
    )

    assert cache.last_get_key == expected_key
    assert llm.calls == 0
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
):
    llm = FakeLLMClient(result={})
    cache = FakeRedisCache()

    with pytest.raises(ValueError):
        map_speakers_to_roles(
            utterances=utterances,
            llm_client=llm,
            cache=cache,
            prompt_id=prompt_id,
            ttl_seconds=300,
        )


@pytest.mark.unit
def test_should_raise_value_error_when_llm_output_missing_one_label(
    utterances_two_speakers: list[dict[str, Any]],
    prompt_id: str,
):
    llm_result = {
        "speaker_roles": {
            "A": {"role": "therapist", "confidence": 0.9, "reason": "Guides."},
        },
        "overall_confidence": 0.9,
    }
    llm = FakeLLMClient(result=llm_result)
    cache = FakeRedisCache()

    with pytest.raises(ValueError):
        map_speakers_to_roles(
            utterances=utterances_two_speakers,
            llm_client=llm,
            cache=cache,
            prompt_id=prompt_id,
            ttl_seconds=300,
        )


@pytest.mark.unit
def test_should_raise_value_error_when_llm_assigns_therapist_twice(
    utterances_two_speakers: list[dict[str, Any]],
    prompt_id: str,
):
    llm_result = {
        "speaker_roles": {
            "A": {"role": "therapist", "confidence": 0.9, "reason": "Guides."},
            "B": {"role": "therapist", "confidence": 0.8, "reason": "Also guides."},
        },
        "overall_confidence": 0.85,
    }
    llm = FakeLLMClient(result=llm_result)
    cache = FakeRedisCache()

    with pytest.raises(ValueError):
        map_speakers_to_roles(
            utterances=utterances_two_speakers,
            llm_client=llm,
            cache=cache,
            prompt_id=prompt_id,
            ttl_seconds=300,
        )


@pytest.mark.unit
@pytest.mark.parametrize(
    "llm_result",
    [
        (
            {
                "speaker_roles": {
                    "A": {"role": "therapist", "confidence": "0.9", "reason": "Guides."},
                    "B": {"role": "patient", "confidence": 0.8, "reason": "Shares."},
                },
                "overall_confidence": 0.85,
            }
        ),
        (
            {
                "speaker_roles": {
                    "A": {"role": "therapist", "confidence": 1.1, "reason": "Guides."},
                    "B": {"role": "patient", "confidence": 0.8, "reason": "Shares."},
                },
                "overall_confidence": 0.85,
            }
        ),
        (
            {
                "speaker_roles": {
                    "A": {"role": "therapist", "confidence": 0.9, "reason": "Guides."},
                    "B": {"role": "patient", "confidence": 0.8, "reason": "Shares."},
                },
                "overall_confidence": -0.1,
            }
        ),
    ],
)
def test_should_raise_value_error_when_confidence_not_number_or_out_of_range(
    utterances_two_speakers: list[dict[str, Any]],
    prompt_id: str,
    llm_result: dict[str, Any],
):
    llm = FakeLLMClient(result=llm_result)
    cache = FakeRedisCache()

    with pytest.raises(ValueError):
        map_speakers_to_roles(
            utterances=utterances_two_speakers,
            llm_client=llm,
            cache=cache,
            prompt_id=prompt_id,
            ttl_seconds=300,
        )


@pytest.mark.unit
def test_should_raise_value_error_when_reason_too_long(
    utterances_two_speakers: list[dict[str, Any]],
    prompt_id: str,
):
    llm_result = {
        "speaker_roles": {
            "A": {
                "role": "therapist",
                "confidence": 0.9,
                "reason": "x" * 121,
            },
            "B": {"role": "patient", "confidence": 0.8, "reason": "Shares."},
        },
        "overall_confidence": 0.85,
    }
    llm = FakeLLMClient(result=llm_result)
    cache = FakeRedisCache()

    with pytest.raises(ValueError):
        map_speakers_to_roles(
            utterances=utterances_two_speakers,
            llm_client=llm,
            cache=cache,
            prompt_id=prompt_id,
            ttl_seconds=300,
        )
