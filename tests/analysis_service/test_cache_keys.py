import hashlib

import pytest

from src.analysis_service.cache_keys import (
    llm_chunk_cache_key,
    speaker_role_mapping_cache_key,
    utterance_tagging_cache_key,
)


# --- Fixtures ---


# --- Unit Tests ---


@pytest.mark.unit
@pytest.mark.parametrize(
    "chunk1,chunk2,prompt1,prompt2,should_be_equal",
    [
        ("stress text", "stress text", "v1", "v1", True),
        ("chunk1", "chunk2", "v1", "v1", False),
        ("stress text", "stress text", "v1", "v2", False),
    ],
)
def test_llm_chunk_cache_key_should_be_deterministic_and_unique(
    chunk1: str,
    chunk2: str,
    prompt1: str,
    prompt2: str,
    should_be_equal: bool,
) -> None:
    key1 = llm_chunk_cache_key(chunk=chunk1, prompt_id=prompt1)
    key2 = llm_chunk_cache_key(chunk=chunk2, prompt_id=prompt2)

    if should_be_equal:
        assert key1 == key2
    else:
        assert key1 != key2


@pytest.mark.unit
def test_speaker_role_mapping_cache_key_should_match_sha256_of_payload(
    utterances_two_speakers: list[dict[str, str]],
) -> None:
    prompt_id = "speaker-role-mapping-v1"

    key = speaker_role_mapping_cache_key(utterances=utterances_two_speakers, prompt_id=prompt_id)

    # The mapper cache key is defined as: sha256(json.dumps({prompt_id, utterances}, sort_keys=True)).
    payload = {"prompt_id": prompt_id, "utterances": utterances_two_speakers}
    expected_digest = hashlib.sha256(
        __import__("json").dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    assert key == f"speaker_role_mapping:{expected_digest}"


@pytest.mark.unit
def test_speaker_role_mapping_cache_key_should_change_when_prompt_id_changes(
    utterances_two_speakers: list[dict[str, str]],
) -> None:
    key1 = speaker_role_mapping_cache_key(utterances=utterances_two_speakers, prompt_id="v1")
    key2 = speaker_role_mapping_cache_key(utterances=utterances_two_speakers, prompt_id="v2")
    assert key1 != key2


@pytest.mark.unit
def test_utterance_tagging_cache_key_should_match_sha256_of_payload(
    utterances_two_speakers: list[dict[str, str]],
) -> None:
    prompt_id = "utterance-tagging-v1"

    key = utterance_tagging_cache_key(utterances=utterances_two_speakers, prompt_id=prompt_id)

    payload = {"prompt_id": prompt_id, "utterances": utterances_two_speakers}
    expected_digest = hashlib.sha256(
        __import__("json").dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    assert key == f"utterance_tagging:{expected_digest}"
