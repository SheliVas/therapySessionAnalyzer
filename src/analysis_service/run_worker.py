from pymongo import MongoClient

from src.analysis_service.config import load_config
from src.analysis_service.domain import AnalysisBackend, AnalysisResult, analyze_transcript
from src.analysis_service.mongo_repository import MongoAnalysisRepository
from src.analysis_service.rabbitmq_consumer import RabbitMQTranscriptCreatedConsumer
from src.analysis_service.rabbitmq_publisher import RabbitMQAnalysisEventPublisher
from src.analysis_service.worker import (
    AnalysisEventPublisher,
    AnalysisRepository,
    AnalysisCompletedEvent,
)
from src.shared.minio_storage import MinioStorage
from src.shared.videos_repository import MongoVideosRepository
from src.shared.config import get_minio_config
from src.transcription_service.domain import TranscriptCreatedEvent


class SimpleWordCountBackend(AnalysisBackend):
    def analyze(self, transcript_text: str) -> AnalysisResult:
        words = transcript_text.split()
        return AnalysisResult(
            video_id="",
            word_count=len(words),
            extra={"backend": "simple-word-count"},
        )


def main() -> None:
    config = load_config()
    minio_config = get_minio_config()
    storage_client = MinioStorage(minio_config)

    mongo_client = MongoClient(config.mongo_uri)
    videos_repository = MongoVideosRepository(mongo_client, db_name=config.mongo_db_name)
    repository = MongoAnalysisRepository(mongo_client, db_name=config.mongo_db_name)

    backend = SimpleWordCountBackend()
    publisher = RabbitMQAnalysisEventPublisher(config.publisher)

    consumer = RabbitMQTranscriptCreatedConsumer(
        config=config.consumer,
        backend=backend,
        publisher=publisher,
        repository=repository,
        storage_client=storage_client,
        videos_repository=videos_repository,
    )

    consumer.run_forever()


if __name__ == "__main__":
    main()
