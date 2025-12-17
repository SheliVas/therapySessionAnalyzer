import assemblyai as aai
from src.transcription_service.domain import TranscriptionBackend, TranscriptionError


class AssemblyAITranscriptionBackend(TranscriptionBackend):
    def __init__(self, api_key: str, base_url: str | None = None):
        self.api_key = api_key
        self.base_url = base_url
        aai.settings.api_key = self.api_key
        if self.base_url:
            aai.settings.base_url = self.base_url

    def transcribe(self, audio_bytes: bytes) -> str:
        config = aai.TranscriptionConfig(
            speaker_labels=True,
            speech_models=["universal"]
        )

        transcriber = aai.Transcriber(config=config)
        transcript = transcriber.transcribe(audio_bytes)

        if transcript.status == "error":
            raise TranscriptionError(f"Transcription failed: {transcript.error}")

        formatted_transcript = []
        for utterance in transcript.utterances:
            formatted_transcript.append(f"Speaker {utterance.speaker}: {utterance.text}")

        return "\n".join(formatted_transcript)
