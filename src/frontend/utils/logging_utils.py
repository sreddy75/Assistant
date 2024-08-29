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

def log_critical(logger, message):
    """
    Log a critical message.

    Args:
    logger (logging.Logger): The logger instance
    message (str): The critical message
    """
    logger.critical(message)

def get_logger(name):
    """
    Get a logger instance with the given name.

    Args:
    name (str): The name for the logger

    Returns:
    logging.Logger: A configured logger instance
    """
    return logging.getLogger(name)

def set_log_level(level):
    """
    Set the log level for the root logger.

    Args:
    level (str): The log level (e.g., 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
    """
    logging.getLogger().setLevel(getattr(logging, level))

def add_file_handler(logger, filename):
    """
    Add a file handler to the logger.

    Args:
    logger (logging.Logger): The logger instance
    filename (str): The name of the log file
    """
    file_handler = logging.FileHandler(filename)
    file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(file_handler)

# Example usage
if __name__ == "__main__":
    logger = setup_logging()
    log_info(logger, "This is an info message")
    log_warning(logger, "This is a warning message")
    log_error(logger, "This is an error message")
    log_debug(logger, "This is a debug message")
    log_critical(logger, "This is a critical message")