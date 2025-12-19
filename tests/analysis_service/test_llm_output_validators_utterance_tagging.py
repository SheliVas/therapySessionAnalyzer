import pytest
from typing import Any
from src.analysis_service.llm_output_validators import validate_utterance_tagging_output

@pytest.mark.unit
def test_should_return_output_when_valid_utterance_tagging_schema() -> None:
    llm_result = {
        "utterances": [
            {"topic": "greeting", "emotion": "neutral"},
            {"topic": "feelings", "emotion": "anxious"}
        ]
    }
    expected_length = 2
    
    validated = validate_utterance_tagging_output(llm_result, expected_length=expected_length)
    
    assert validated == llm_result

@pytest.mark.unit
def test_should_raise_value_error_when_not_dict() -> None:
    llm_result = ["not", "a", "dict"]
    
    with pytest.raises(ValueError, match="LLM output must be a JSON object"):
        validate_utterance_tagging_output(llm_result, expected_length=3)

@pytest.mark.unit
def test_should_raise_value_error_when_missing_utterances_key() -> None:
    llm_result = {"wrong_key": []}
    
    with pytest.raises(ValueError, match="LLM output must contain 'utterances' key"):
        validate_utterance_tagging_output(llm_result, expected_length=0)

@pytest.mark.unit
def test_should_raise_value_error_when_utterances_not_list() -> None:
    llm_result = {"utterances": "not a list"}
    
    with pytest.raises(ValueError, match="'utterances' must be a list"):
        validate_utterance_tagging_output(llm_result, expected_length=0)

@pytest.mark.unit
def test_should_raise_value_error_when_length_mismatch() -> None:
    llm_result = {
        "utterances": [
            {"topic": "greeting", "emotion": "neutral"}
        ]
    }
    expected_length = 2
    
    with pytest.raises(ValueError, match="LLM output length mismatch"):
        validate_utterance_tagging_output(llm_result, expected_length=expected_length)

@pytest.mark.unit
def test_should_raise_value_error_when_item_missing_keys() -> None:
    llm_result = {
        "utterances": [
            {"topic": "greeting"} # missing emotion
        ]
    }
    expected_length = 1
    
    with pytest.raises(ValueError, match="Each utterance must have 'topic' and 'emotion'"):
        validate_utterance_tagging_output(llm_result, expected_length=expected_length)
