"""Shared RabbitMQ infrastructure for publishers and consumers.

Provides base classes to reduce boilerplate across services while maintaining
the flexibility for service-specific event types.
"""

import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Callable, TypeVar

import pika
from pydantic import BaseModel

from src.shared.config import RabbitMQConnectionConfig

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class RabbitMQPublisherBase(ABC):
    """Base class for RabbitMQ publishers with message persistence.
    
    Subclasses should define the specific event type and publish method.
    """
    
    def __init__(self, config: RabbitMQConnectionConfig) -> None:
        self._config = config
    
    def _publish(self, queue_name: str, event: BaseModel) -> None:
        """Publish a Pydantic event to RabbitMQ with persistence.
        
        Args:
            queue_name: Target queue name.
            event: Pydantic model to publish.
        """
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
            channel.queue_declare(queue=queue_name, durable=True)
            
            body = event.model_dump_json().encode("utf-8")
            
            channel.basic_publish(
                exchange="",
                routing_key=queue_name,
                body=body,
                properties=pika.BasicProperties(delivery_mode=2),
            )
        finally:
            connection.close()


class RabbitMQConsumerBase(ABC):
    """Base class for RabbitMQ consumers with QoS and error handling.
    
    Subclasses should implement _process_message to handle specific event types.
    """
    
    def __init__(self, config: RabbitMQConnectionConfig, queue_name: str) -> None:
        self._config = config
        self._queue_name = queue_name
    
    @abstractmethod
    def _process_message(self, data: dict[str, Any]) -> None:
        """Process a parsed message. Implement in subclass.
        
        Args:
            data: Parsed JSON data from the message body.
            
        Raises:
            Exception: Any exception will cause message to be nack'd.
        """
        ...
    
    def run_forever(self) -> None:
        """Start consuming messages from the queue.
        
        Connects to RabbitMQ, declares the queue with QoS, and starts
        consuming messages. Each message is parsed and passed to
        _process_message for handling.
        """
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
        channel = connection.channel()
        channel.queue_declare(queue=self._queue_name, durable=True)
        channel.basic_qos(prefetch_count=1)
        
        logger.info(
            "rabbitmq.connected host=%s queue=%s",
            self._config.host,
            self._queue_name,
        )
        
        def _callback(ch, method, properties, body: bytes) -> None:
            try:
                data = json.loads(body.decode("utf-8"))
                logger.info(
                    "rabbitmq.message.received delivery_tag=%s",
                    method.delivery_tag,
                )
                
                self._process_message(data)
                
                ch.basic_ack(delivery_tag=method.delivery_tag)
                logger.info(
                    "rabbitmq.message.acknowledged delivery_tag=%s",
                    method.delivery_tag,
                )
            except Exception as e:
                logger.exception("Error processing message: %s", e)
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        
        channel.basic_consume(
            queue=self._queue_name,
            on_message_callback=_callback,
        )
        
        channel.start_consuming()
