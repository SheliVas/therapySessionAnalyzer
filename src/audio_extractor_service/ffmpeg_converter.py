"""FFmpeg-based audio converter for extracting audio from video files."""

from io import BytesIO
import subprocess

from src.audio_extractor_service.domain import AudioConverter


class FFmpegAudioConverter(AudioConverter):
    """FFmpeg-based audio converter.
    
    Converts video bytes to MP3 audio using FFmpeg subprocess.
    """

    def convert(self, video_bytes: bytes) -> bytes:
        """Convert video bytes to audio (MP3) using FFmpeg.
        
        Args:
            video_bytes: Raw video file bytes.
            
        Returns:
            MP3 audio bytes.
            
        Raises:
            RuntimeError: If FFmpeg conversion fails.
        """
        try:
            process = subprocess.Popen(
                [
                    "ffmpeg",
                    "-i", "pipe:0",
                    "-q:a", "9",
                    "-f", "mp3",
                    "pipe:1",
                ],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            audio_bytes, stderr = process.communicate(input=video_bytes)

            if process.returncode != 0:
                raise RuntimeError(f"FFmpeg conversion failed: {stderr.decode()}")

            return audio_bytes
        except FileNotFoundError as e:
            raise RuntimeError("FFmpeg not found. Please install FFmpeg.") from e
        except Exception as e:
            raise RuntimeError(f"Audio conversion failed: {str(e)}") from e
