from pydantic import BaseModel


class VideoSummary(BaseModel):
    video_id: str
    word_count: int
    status: str
    analysis: dict


class MongoReportRepository:
    def __init__(self, client, db_name: str = "therapy_analysis"):
        self.client = client
        self.db = client[db_name]
        self.analysis_collection = self.db["analysis_results"]
        self.videos_collection = self.db["videos"]
    
    def list_videos(self) -> list[VideoSummary]:
        pipeline = [
            {"$match": {"status": "analyzed"}},
            {
                "$lookup": {
                    "from": "analysis_results",
                    "localField": "video_id",
                    "foreignField": "video_id",
                    "as": "analysis"
                }
            },
            {"$unwind": "$analysis"},
            {
                "$project": {
                    "video_id": 1,
                    "status": 1,
                    "word_count": "$analysis.word_count",
                    "analysis": "$analysis.analysis"
                }
            }
        ]
        documents = list(self.videos_collection.aggregate(pipeline))
        return [VideoSummary(**doc) for doc in documents]

    def get_video(self, video_id: str) -> VideoSummary | None:
        video_doc = self.videos_collection.find_one({"video_id": video_id})
        if not video_doc:
            return None
        
        analysis_doc = self.analysis_collection.find_one({"video_id": video_id})
        if not analysis_doc:
            return None
            
        return VideoSummary(
            video_id=video_id,
            status=video_doc["status"],
            word_count=analysis_doc["word_count"],
            analysis=analysis_doc["analysis"]
        )
