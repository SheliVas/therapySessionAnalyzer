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
