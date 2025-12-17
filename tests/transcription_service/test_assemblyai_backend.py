import pytest
from src.transcription_service.backend import AssemblyAITranscriptionBackend
from src.transcription_service.domain import TranscriptionError

@pytest.fixture
def backend():
    return AssemblyAITranscriptionBackend(api_key="test_key")

@pytest.mark.unit
def test_should_set_api_key_on_initialization(mocker):
    mock_aai = mocker.patch("src.transcription_service.backend.aai")
    AssemblyAITranscriptionBackend(api_key="test_key")
    assert mock_aai.settings.api_key == "test_key"

@pytest.mark.unit
def test_should_use_assemblyai_sdk_correctly(backend, mocker):
    mock_aai = mocker.patch("src.transcription_service.backend.aai")
    
    mock_transcriber = mocker.Mock()
    mock_aai.Transcriber.return_value = mock_transcriber
    
    mock_transcript = mocker.Mock()
    mock_transcript.status = "completed"
    mock_transcript.utterances = [
        mocker.Mock(speaker="A", text="Hello"),
        mocker.Mock(speaker="B", text="world")
    ]
    mock_transcriber.transcribe.return_value = mock_transcript

    audio_bytes = b"fake audio"
    transcript_text = backend.transcribe(audio_bytes)

    assert transcript_text == "Speaker A: Hello\nSpeaker B: world"
    
    # Verify Transcriber was called with correct config
    mock_aai.TranscriptionConfig.assert_called_once()
    config_kwargs = mock_aai.TranscriptionConfig.call_args.kwargs
    assert config_kwargs.get("speaker_labels") is True
    assert "universal" in config_kwargs.get("speech_models", [])

    mock_transcriber.transcribe.assert_called_once_with(audio_bytes)

@pytest.mark.unit
def test_should_raise_transcription_error_on_sdk_failure(backend, mocker):
    mock_aai = mocker.patch("src.transcription_service.backend.aai")
    mock_transcriber = mocker.Mock()
    mock_aai.Transcriber.return_value = mock_transcriber
    
    mock_transcript = mocker.Mock()
    mock_transcript.status = "error"
    mock_transcript.error = "API Error"
    mock_transcriber.transcribe.return_value = mock_transcript

    with pytest.raises(TranscriptionError) as excinfo:
        backend.transcribe(b"audio")
    
    assert "Transcription failed: API Error" in str(excinfo.value)
