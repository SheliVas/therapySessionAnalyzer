import pika

from src.analysis_service.domain import AnalysisCompletedEvent, AnalysisEventPublisher
from src.shared.config import AnalysisCompletedPublisherConfig


class RabbitMQAnalysisEventPublisher(AnalysisEventPublisher):

    def __init__(self, config: AnalysisCompletedPublisherConfig) -> None:
        self._config = config

    def publish_analysis_completed(self, event: AnalysisCompletedEvent) -> None:
        """Publish an AnalysisCompletedEvent to RabbitMQ."""
        credentials = pika.PlainCredentials(
            self._config.username,
            self._config.password,
        )
        parameters = pika.ConnectionParameters(
            host=self._config.host,
            port=self._config.port,
            credentials=credentials,
            heartbeat=0,
        )

        connection = pika.BlockingConnection(parameters)
        try:
            channel = connection.channel()

            channel.queue_declare(queue=self._config.queue_name, durable=True)

            body = event.model_dump_json().encode("utf-8")

            channel.basic_publish(
                exchange="",
                routing_key=self._config.queue_name,
                body=body,
                properties=pika.BasicProperties(delivery_mode=2),
            )
        finally:
            connection.close()
