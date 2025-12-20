import os
import pytest
import httpx
from src.analysis_service.config import load_config
from src.analysis_service.llm_client import GeminiLLMClient, get_llm_client

# --- Fixtures ---

@pytest.fixture
def llm_config():
    return {
        "api_key": "test-key",
        "model": "gemini-2.5-flash",
        "base_url": "https://generativelanguage.googleapis.com",
        "timeout": 10.0,
    }

# --- Unit Tests ---

@pytest.mark.unit
def test_should_return_gemini_client_when_api_key_provided(llm_config):
    client = get_llm_client(**llm_config)
    assert isinstance(client, GeminiLLMClient)
    assert client.api_key == "test-key"

@pytest.mark.unit
def test_gemini_client_should_build_request_and_parse_response(mocker, llm_config):
    mock_response = mocker.MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {"text": '{"emotion": "happy", "summary": "A good session"}'}
                    ]
                }
            }
        ]
    }

    mock_client_instance = mocker.MagicMock()
    mock_client_instance.__enter__.return_value = mock_client_instance
    mock_client_instance.post.return_value = mock_response
    mocker.patch(
        "src.analysis_service.llm_client.httpx.Client", return_value=mock_client_instance
    )

    client = GeminiLLMClient(**llm_config)
    result = client.analyze_transcript("Hello world")

    assert result == {"emotion": "happy", "summary": "A good session"}
    mock_client_instance.post.assert_called_once()
    args, kwargs = mock_client_instance.post.call_args
    assert args[0].endswith("/v1beta/models/gemini-2.5-flash:generateContent")
    assert kwargs["headers"]["x-goog-api-key"] == "test-key"
    body = kwargs["json"]
    assert body["contents"][0]["role"] == "user"
    assert body["contents"][0]["parts"][0]["text"] == "Hello world"
    assert body["generationConfig"]["responseMimeType"] == "application/json"
    assert body["generationConfig"]["temperature"] == 0

@pytest.mark.unit
def test_gemini_client_should_handle_dict_input_with_system_instruction(mocker, llm_config):
    mock_response = mocker.MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {"text": '{"result": "ok"}'}
                    ]
                }
            }
        ]
    }

    mock_client_instance = mocker.MagicMock()
    mock_client_instance.__enter__.return_value = mock_client_instance
    mock_client_instance.post.return_value = mock_response
    mocker.patch(
        "src.analysis_service.llm_client.httpx.Client", return_value=mock_client_instance
    )

    client = GeminiLLMClient(**llm_config)
    result = client.analyze_transcript({
        "system": "You are a helpful assistant",
        "user": "Hello"
    })

    assert result == {"result": "ok"}
    args, kwargs = mock_client_instance.post.call_args
    body = kwargs["json"]
    assert body["systemInstruction"]["parts"][0]["text"] == "You are a helpful assistant"
    assert body["contents"][0]["parts"][0]["text"] == "Hello"

@pytest.mark.unit
def test_gemini_client_should_raise_on_invalid_json_response(mocker, llm_config):
    mock_response = mocker.MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {"text": "not-json"}
                    ]
                }
            }
        ]
    }

    mock_client_instance = mocker.MagicMock()
    mock_client_instance.__enter__.return_value = mock_client_instance
    mock_client_instance.post.return_value = mock_response
    mocker.patch(
        "src.analysis_service.llm_client.httpx.Client", return_value=mock_client_instance
    )

    client = GeminiLLMClient(**llm_config)

    with pytest.raises(ValueError, match="LLM output was not valid JSON"):
        client.analyze_transcript("Hello world")

@pytest.mark.unit
def test_config_wiring_should_select_gemini_client_when_key_present(mocker):
    mocker.patch.dict(os.environ, {"GEMINI_API_KEY": "real-key"}, clear=True)
    config = load_config()
    client = get_llm_client(
        api_key=config.llm.api_key,
        model=config.llm.model,
        base_url=config.llm.base_url,
        timeout=config.llm.timeout,
    )
    assert isinstance(client, GeminiLLMClient)

@pytest.mark.unit
def test_config_wiring_should_raise_error_when_key_missing(mocker):
    mocker.patch.dict(os.environ, {}, clear=True)
    with pytest.raises(ValueError, match="GEMINI_API_KEY must be provided"):
        load_config()

@pytest.mark.unit
def test_gemini_client_should_retry_on_429(mocker, llm_config):
    mock_429 = mocker.MagicMock()
    mock_429.status_code = 429
    mock_429.raise_for_status.side_effect = httpx.HTTPStatusError("Too Many Requests", request=mocker.Mock(), response=mock_429)

    mock_200 = mocker.MagicMock()
    mock_200.status_code = 200
    mock_200.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {"text": '{"result": "success"}'}
                    ]
                }
            }
        ]
    }

    mock_client_instance = mocker.MagicMock()
    mock_client_instance.__enter__.return_value = mock_client_instance
    mock_client_instance.post.side_effect = [httpx.HTTPStatusError("Too Many Requests", request=mocker.Mock(), response=mock_429), httpx.HTTPStatusError("Too Many Requests", request=mocker.Mock(), response=mock_429), mock_200]
    
    mocker.patch(
        "src.analysis_service.llm_client.httpx.Client", return_value=mock_client_instance
    )
    
    mocker.patch("time.sleep")

    client = GeminiLLMClient(**llm_config)
    result = client.analyze_transcript("Hello world")

    assert result == {"result": "success"}
    assert mock_client_instance.post.call_count == 3

@pytest.mark.unit
def test_gemini_client_should_fail_after_max_retries(mocker, llm_config):
    mock_429 = mocker.MagicMock()
    mock_429.status_code = 429
    mock_429.raise_for_status.side_effect = httpx.HTTPStatusError("Too Many Requests", request=mocker.Mock(), response=mock_429)

    mock_client_instance = mocker.MagicMock()
    mock_client_instance.__enter__.return_value = mock_client_instance
    # Always fail
    mock_client_instance.post.side_effect = httpx.HTTPStatusError("Too Many Requests", request=mocker.Mock(), response=mock_429)
    
    mocker.patch(
        "src.analysis_service.llm_client.httpx.Client", return_value=mock_client_instance
    )
    
    mocker.patch("time.sleep")

    client = GeminiLLMClient(**llm_config)
    
    with pytest.raises(httpx.HTTPStatusError):
        client.analyze_transcript("Hello world")
    
    assert mock_client_instance.post.call_count == 5
