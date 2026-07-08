# Secure, structured logging setup
import logging
import sys

from pythonjsonlogger import jsonlogger  # pip install python-json-logger


def get_logger(name: str) -> logging.Logger:
    """Get configured logger with JSON output for production"""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger  # Already configured
    
    logger.setLevel(logging.INFO)
    
    # Console handler (development)
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    
    # JSON formatter for structured logs (security: no sensitive data)
    formatter = jsonlogger.JsonFormatter(
        '%(asctime)s %(name)s %(levelname)s %(message)s',
        rename_fields={"asctime": "timestamp", "name": "logger", "levelname": "level"}
    )
    console.setFormatter(formatter)
    
    logger.addHandler(console)
    logger.propagate = False  # Avoid duplicate logs
    
    return logger