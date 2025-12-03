from pydantic import BaseModel


class VideoSummary(BaseModel):
    video_id: str
    word_count: int
    extra: dict


class MongoReportRepository:
    def __init__(self, client, db_name: str = "therapy_analysis"):
        self.client = client
        self.db = client[db_name]
        self.collection = self.db["analysis_results"]
    
    def list_videos(self) -> list[VideoSummary]:
        documents = list(self.collection.find())
        return [VideoSummary(**doc) for doc in documents]
