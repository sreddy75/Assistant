import logging
from config.settings import LOG_LEVEL

def setup_logging():
    """
    Set up logging for the application.
    """
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL),
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

def log_error(logger, message, exc_info=False):
    """
    Log an error message.
    
    Args:
    logger (logging.Logger): The logger instance
    message (str): The error message
    exc_info (bool): Whether to include exception information
    """
    logger.error(message, exc_info=exc_info)

def log_info(logger, message):
    """
    Log an info message.
    
    Args:
    logger (logging.Logger): The logger instance
    message (str): The info message
    """
    logger.info(message)

def log_warning(logger, message):
    """
    Log a warning message.
    
    Args:
    logger (logging.Logger): The logger instance
    message (str): The warning message
    """
    logger.warning(message)

def log_debug(logger, message):
    """
    Log a debug message.
    
    Args:
    logger (logging.Logger): The logger instance
    message (str): The debug message
    """
    logger.debug(message)