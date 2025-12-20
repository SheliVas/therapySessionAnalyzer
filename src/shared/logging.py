"""Centralized logging configuration for all services."""

import logging
import sys
from typing import Optional


def configure_logging(
    level: int = logging.INFO,
    service_name: Optional[str] = None,
    format_string: Optional[str] = None,
) -> None:
    """Configure logging for the application.
    
    Args:
        level: Logging level (default: INFO).
        service_name: Optional service name to include in log format.
        format_string: Custom format string (overrides default).
    """
    if format_string is None:
        if service_name:
            format_string = (
                f"%(asctime)s | {service_name} | %(levelname)s | "
                "%(name)s | %(message)s"
            )
        else:
            format_string = (
                "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
            )
    
    logging.basicConfig(
        level=level,
        format=format_string,
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the given name.
    
    Args:
        name: Logger name (typically __name__).
        
    Returns:
        Configured logger instance.
    """
    return logging.getLogger(name)
