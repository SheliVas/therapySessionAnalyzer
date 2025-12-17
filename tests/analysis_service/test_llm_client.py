import pytest
from unittest.mock import MagicMock
from src.analysis_service.llm_client import OpenAILLMClient, get_llm_client
from src.analysis_service.config import load_config
import os

# --- Fixtures ---

@pytest.fixture
def llm_config():
    return {
        "api_key": "test-key",
        "model": "gpt-5-mini",
        "base_url": "https://api.openai.com/v1",
        "timeout": 10.0
    }

# --- Unit Tests ---

@pytest.mark.unit
def test_should_return_openai_client_when_api_key_provided(llm_config):
    client = get_llm_client(**llm_config)
    assert isinstance(client, OpenAILLMClient)
    assert client.api_key == "test-key"

@pytest.mark.unit
def test_openai_client_should_build_request_and_parse_response(mocker, llm_config):
    # Mock httpx.Client
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": '{"emotion": "happy", "summary": "A good session"}'
                }
            }
        ]
    }
    
    mock_client_instance = MagicMock()
    mock_client_instance.__enter__.return_value = mock_client_instance
    mock_client_instance.post.return_value = mock_response
    mocker.patch("src.analysis_service.llm_client.httpx.Client", return_value=mock_client_instance)

    client = OpenAILLMClient(**llm_config)
    result = client.analyze_transcript("Hello world")

    assert result == {"emotion": "happy", "summary": "A good session"}
    mock_client_instance.post.assert_called_once()
    # Verify payload (minimal check)
    args, kwargs = mock_client_instance.post.call_args
    assert kwargs["json"]["model"] == "gpt-5-mini"
    assert any("Hello world" in msg["content"] for msg in kwargs["json"]["messages"])

@pytest.mark.unit
def test_config_wiring_should_select_openai_client_when_key_present(mocker):
    mocker.patch.dict(os.environ, {"LLM_API_KEY": "real-key"})
    config = load_config()
    client = get_llm_client(
        api_key=config.llm.api_key,
        model=config.llm.model,
        base_url=config.llm.base_url,
        timeout=config.llm.timeout
    )
    assert isinstance(client, OpenAILLMClient)

@pytest.mark.unit
def test_config_wiring_should_raise_error_when_key_missing(mocker):
    mocker.patch.dict(os.environ, {"LLM_API_KEY": ""})
    config = load_config()
    with pytest.raises(ValueError, match="API key must be provided"):
        get_llm_client(
            api_key=config.llm.api_key,
            model=config.llm.model,
            base_url=config.llm.base_url,
            timeout=config.llm.timeout
        )
