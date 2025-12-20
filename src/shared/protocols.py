"""Shared protocols for dependency injection across services.

These protocols define contracts that domain logic depends on,
allowing infrastructure implementations to be swapped for testing.
"""

from datetime import datetime
from typing import Optional, Protocol


class StorageClient(Protocol):
    """Protocol for file storage operations (MinIO, S3, etc.)."""

    def upload_file(self, bucket: str, key: str, content: bytes) -> None:
        """Upload a file to storage.

        Args:
            bucket: Bucket name.
            key: Object key (path within bucket).
            content: File content bytes.
        """
        ...

    def download_file(self, bucket: str, key: str) -> bytes:
        """Download a file from storage.

        Args:
            bucket: Bucket name.
            key: Object key (path within bucket).

        Returns:
            Raw bytes of the object.

        Raises:
            ValueError: If object is not found.
        """
        ...


class VideosRepository(Protocol):
    """Protocol for managing video metadata status throughout the pipeline."""

    def upsert_on_upload(
        self,
        video_id: str,
        filename: str,
        storage_path: str,
        uploaded_at: Optional[datetime] = None,
    ) -> None:
        """Upsert video metadata on upload.

        Args:
            video_id: Unique video identifier.
            filename: Original filename.
            storage_path: Storage location (bucket/key).
            uploaded_at: Upload timestamp.
        """
        ...

    def mark_audio_extracted(self, video_id: str, audio_path: str) -> None:
        """Mark a video as having audio extracted and store the audio path.

        Args:
            video_id: Unique video identifier.
            audio_path: Path where the extracted audio is stored (bucket/key).

        Raises:
            VideoNotFoundError: If the video does not exist.
        """
        ...

    def mark_transcribed(self, video_id: str, transcript_path: str) -> None:
        """Mark a video as transcribed and store the transcript path.

        Args:
            video_id: Unique video identifier.
            transcript_path: Path where the transcript is stored (bucket/key).

        Raises:
            VideoNotFoundError: If the video does not exist.
        """
        ...

    def mark_analyzed(self, video_id: str, word_count: Optional[int] = None) -> None:
        """Mark a video as analyzed and optionally set word count.

        Args:
            video_id: Unique video identifier.
            word_count: Word count from analysis (optional).

        Raises:
            VideoNotFoundError: If the video does not exist.
        """
        ...
