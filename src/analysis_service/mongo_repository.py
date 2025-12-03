from src.analysis_service.worker import AnalysisCompletedEvent


class MongoAnalysisRepository:

    def __init__(self, client, db_name: str = "therapy_analysis") -> None:
        """Initialize the repository with a MongoDB client.

        Args:
            client: A MongoDB client (or mongomock client for testing).
            db_name: The database name to use. Defaults to "therapy_analysis".
        """
        self._collection = client[db_name]["analysis_results"]

    def save_analysis(self, event: AnalysisCompletedEvent) -> None:
        """Save (upsert) an AnalysisCompletedEvent to the collection.

        Args:
            event: The AnalysisCompletedEvent to save.
        """
        self._collection.update_one(
            {"video_id": event.video_id},
            {
                "$set": {
                    "video_id": event.video_id,
                    "word_count": event.word_count,
                    "extra": event.extra,
                }
            },
            upsert=True,
        )

    def get_analysis(self, video_id: str) -> AnalysisCompletedEvent | None:
        """Retrieve an AnalysisCompletedEvent by video_id.

        Args:
            video_id: The video_id to look up.

        Returns:
            The AnalysisCompletedEvent if found, else None.
        """
        doc = self._collection.find_one({"video_id": video_id})
        if doc is None:
            return None
        return AnalysisCompletedEvent(
            video_id=doc["video_id"],
            word_count=doc["word_count"],
            extra=doc["extra"],
        )

