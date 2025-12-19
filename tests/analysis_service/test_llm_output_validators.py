import pytest

from src.analysis_service.llm_output_validators import validate_speaker_role_mapping_output


# --- Fixtures ---


# --- Unit Tests ---


@pytest.mark.unit
def test_should_return_output_when_valid_schema(speaker_labels: list[str]) -> None:
    llm_result = {
        "speaker_roles": {
            "A": {"role": "patient", "confidence": 0.86, "reason": "Shares problems and feelings."},
            "B": {"role": "therapist", "confidence": 0.91, "reason": "Asks guiding questions."},
        },
        "overall_confidence": 0.9,
    }

    validated = validate_speaker_role_mapping_output(llm_result, speaker_labels=speaker_labels)

    assert validated == llm_result


@pytest.mark.unit
def test_should_raise_value_error_when_missing_one_label(speaker_labels: list[str]) -> None:
    llm_result = {
        "speaker_roles": {
            "A": {"role": "therapist", "confidence": 0.9, "reason": "Guides."},
        },
        "overall_confidence": 0.9,
    }

    with pytest.raises(ValueError):
        validate_speaker_role_mapping_output(llm_result, speaker_labels=speaker_labels)


@pytest.mark.unit
def test_should_raise_value_error_when_assigns_therapist_twice(speaker_labels: list[str]) -> None:
    llm_result = {
        "speaker_roles": {
            "A": {"role": "therapist", "confidence": 0.9, "reason": "Guides."},
            "B": {"role": "therapist", "confidence": 0.8, "reason": "Also guides."},
        },
        "overall_confidence": 0.85,
    }

    with pytest.raises(ValueError):
        validate_speaker_role_mapping_output(llm_result, speaker_labels=speaker_labels)


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
    speaker_labels: list[str],
    llm_result: dict,
) -> None:
    with pytest.raises(ValueError):
        validate_speaker_role_mapping_output(llm_result, speaker_labels=speaker_labels)


@pytest.mark.unit
def test_should_raise_value_error_when_reason_too_long(speaker_labels: list[str]) -> None:
    llm_result = {
        "speaker_roles": {
            "A": {"role": "therapist", "confidence": 0.9, "reason": "x" * 121},
            "B": {"role": "patient", "confidence": 0.8, "reason": "Shares."},
        },
        "overall_confidence": 0.85,
    }

    with pytest.raises(ValueError):
        validate_speaker_role_mapping_output(llm_result, speaker_labels=speaker_labels)
