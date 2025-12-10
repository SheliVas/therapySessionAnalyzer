from datetime import datetime
from typing import Optional
from src.shared.exceptions import VideoNotFoundError


class MongoVideosRepository:
    """Repository for managing video metadata in MongoDB."""
    
    def __init__(self, client, db_name: str = "therapy_analysis") -> None:
        """Initialize the repository with a MongoDB client and database name.
        
        Args:
            client: MongoDB client instance.
            db_name: Database name (default: "therapy_analysis").
        """
        self._collection = client[db_name]["videos"]
    
    def upsert_on_upload(
        self,
        video_id: str,
        filename: str,
        storage_path: str,
        uploaded_at: Optional[datetime] = None,
    ) -> None:
        """Upsert a video document on upload.
        
        Args:
            video_id: Unique video identifier.
            filename: Original filename.
            storage_path: Path where the file is stored.
            uploaded_at: Timestamp of upload (optional).
        """
        update_data = {
            "video_id": video_id,
            "filename": filename,
            "storage_path": storage_path,
            "status": "uploaded",
        }
        if uploaded_at is not None:
            update_data["uploaded_at"] = uploaded_at
        
        self._collection.update_one(
            {"video_id": video_id},
            {"$set": update_data},
            upsert=True,
        )
    
    def mark_analyzed(
        self,
        video_id: str,
        word_count: Optional[int] = None,
    ) -> None:
        """Mark a video as analyzed and optionally set word count.
        
        Args:
            video_id: Unique video identifier.
            word_count: Word count from analysis (optional).
            
        Raises:
            VideoNotFoundError: If the video does not exist.
        """
        update_data = {"status": "analyzed"}
        if word_count is not None:
            update_data["word_count"] = word_count
        
        result = self._collection.update_one(
            {"video_id": video_id},
            {"$set": update_data},
            upsert=False,
        )
        
        if result.matched_count == 0:
            raise VideoNotFoundError(f"Video with id {video_id} not found")
