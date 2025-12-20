from __future__ import annotations

from typing import Any


def _is_number_0_1(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    if not isinstance(value, (int, float)):
        return False
    return 0.0 <= float(value) <= 1.0


def validate_speaker_role_mapping_output(result: Any, *, speaker_labels: list[str]) -> dict[str, Any]:
    """Validate strict JSON output for the speaker role mapping prompt.

    Raises ValueError for any schema/content violation.
    Returns the validated dict (unchanged) on success.
    """

    if not isinstance(result, dict):
        raise ValueError("LLM output must be a JSON object")

    expected_top_keys = {"speaker_roles", "overall_confidence"}
    if set(result.keys()) != expected_top_keys:
        raise ValueError("LLM output must have exactly: speaker_roles, overall_confidence")

    speaker_roles = result.get("speaker_roles")
    if not isinstance(speaker_roles, dict):
        raise ValueError("speaker_roles must be an object")

    if set(speaker_roles.keys()) != set(speaker_labels):
        raise ValueError("speaker_roles keys must match the input speaker labels")

    roles_assigned: list[str] = []
    for label in speaker_labels:
        entry = speaker_roles.get(label)
        if not isinstance(entry, dict):
            raise ValueError("Each speaker_roles entry must be an object")

        if set(entry.keys()) != {"role", "confidence", "reason"}:
            raise ValueError("Each speaker_roles entry must have exactly: role, confidence, reason")

        role = entry.get("role")
        if role not in {"therapist", "patient"}:
            raise ValueError("role must be therapist or patient")
        roles_assigned.append(role)

        confidence = entry.get("confidence")
        if not _is_number_0_1(confidence):
            raise ValueError("confidence must be a number in [0,1]")

        reason = entry.get("reason")
        if not isinstance(reason, str):
            raise ValueError("reason must be a string")
        if len(reason) > 120:
            raise ValueError("reason must be <= 120 characters")

    if sorted(roles_assigned) != ["patient", "therapist"]:
        raise ValueError("Exactly one therapist and one patient must be assigned")

    overall_confidence = result.get("overall_confidence")
    if not _is_number_0_1(overall_confidence):
        raise ValueError("overall_confidence must be a number in [0,1]")

    return result


def validate_utterance_tagging_output(result: Any, *, expected_length: int) -> dict[str, Any]:
    """Validate strict JSON output for the utterance tagging prompt.

    Raises ValueError for any schema/content violation.
    Returns the validated dict (unchanged) on success.
    """
    if not isinstance(result, dict):
        raise ValueError("LLM output must be a JSON object")

    if "utterances" not in result:
        raise ValueError("LLM output must contain 'utterances' key")

    utterances = result["utterances"]
    if not isinstance(utterances, list):
        raise ValueError("'utterances' must be a list")

    if len(utterances) != expected_length:
        raise ValueError(f"LLM output length mismatch: expected {expected_length}, got {len(utterances)}")

    for i, utt in enumerate(utterances):
        if not isinstance(utt, dict):
            raise ValueError(f"Utterance at index {i} must be an object")
        if "topic" not in utt or "emotion" not in utt:
            raise ValueError(f"Each utterance must have 'topic' and 'emotion' (failed at index {i})")

    return result


def validate_recommendations_output(data: Any, *, valid_topics: set[str], valid_emotions: set[str]) -> dict[str, Any]:
    """Validate strict JSON output for the therapist recommendations prompt.

    Raises ValueError for any schema/content violation.
    Returns the validated dict (unchanged) on success.
    """
    if not isinstance(data, dict):
        raise ValueError("Output must be a dictionary")
    
    if set(data.keys()) != {"therapist_recommendations"}:
        raise ValueError("output keys must be exactly ['therapist_recommendations']")
    
    recs = data["therapist_recommendations"]
    if not isinstance(recs, list):
        raise ValueError("therapist_recommendations must be a list")
        
    if not (3 <= len(recs) <= 5):
        raise ValueError(f"list length must be between 3 and 5, got {len(recs)}")
        
    valid_priorities = {"high", "medium", "low"}
    required_item_keys = {"title", "rationale", "priority", "related_topics", "target_emotions"}
    
    for item in recs:
        if not isinstance(item, dict):
            raise ValueError("Recommendation item must be a dictionary")
            
        if set(item.keys()) != required_item_keys:
            extra = set(item.keys()) - required_item_keys
            if extra:
                raise ValueError(f"extra keys found: {extra}")
            raise ValueError(f"Item keys must be exactly {required_item_keys}")
            
        if item["priority"] not in valid_priorities:
            raise ValueError(f"Invalid priority: {item['priority']}")
            
        if not isinstance(item["related_topics"], list):
             raise ValueError("related_topics must be a list")
        for topic in item["related_topics"]:
            if topic not in valid_topics:
                raise ValueError(f"related_topics contains topic not in input: {topic}")

        if not isinstance(item["target_emotions"], list):
             raise ValueError("target_emotions must be a list")
        for emotion in item["target_emotions"]:
            if emotion not in valid_emotions:
                raise ValueError(f"target_emotions contains emotion not in input: {emotion}")
    
    return data
