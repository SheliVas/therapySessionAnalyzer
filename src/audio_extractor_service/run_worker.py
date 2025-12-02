from pathlib import Path

from src.audio_extractor_service.config import load_config
from src.audio_extractor_service.rabbitmq_consumer import RabbitMQVideoUploadedConsumer
from src.audio_extractor_service.rabbitmq_publisher import RabbitMQAudioEventPublisher
from src.audio_extractor_service.worker import AudioEventPublisher, AudioExtractedEvent


class LoggingAudioEventPublisher(AudioEventPublisher):
    def publish_audio_extracted(self, event: AudioExtractedEvent) -> None:
        # For now just print; later we’ll publish to RabbitMQ for the next service
        print(f"[audio_extractor] audio extracted: {event.video_id} -> {event.audio_path}")


def main() -> None:
    config = load_config()

    publisher = RabbitMQAudioEventPublisher(config.publisher)
    consumer = RabbitMQVideoUploadedConsumer(
        config=config.consumer,
        base_output_dir=config.base_output_dir,
        publisher=publisher,
    )

    consumer.run_forever()


if __name__ == "__main__":
    main()
