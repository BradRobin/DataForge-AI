import logging
import os
import sys

def setup_logging(log_level: str = "INFO") -> None:
    # Create logs directory if it doesn't exist relative to execution dir
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "dataforge.log")

    # Get root logger
    root_logger = logging.getLogger()
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Convert string level to logging level
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    root_logger.setLevel(numeric_level)

    # Create formatters
    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(numeric_level)
    root_logger.addHandler(console_handler)

    # File Handler
    try:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        file_handler.setLevel(numeric_level)
        root_logger.addHandler(file_handler)
    except Exception as e:
        # If we cannot write to files (e.g. permission issue in some environments), log to console only
        print(f"Warning: Could not create file logger at {log_file} due to {e}. Console logging only.", file=sys.stderr)

    # Configure uvicorn loggers to use our config or suppress noise
    logging.getLogger("uvicorn.error").handlers = root_logger.handlers
    logging.getLogger("uvicorn.access").handlers = root_logger.handlers

    logging.info(f"Logging initialized with level: {log_level}. Logs written to {log_file}")
