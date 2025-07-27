import logging
import sys
import os
from logging.handlers import TimedRotatingFileHandler

# --- Configuration ---
LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "app.log")
LOG_LEVEL = logging.INFO
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# --- Create logs directory if it doesn't exist ---
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# --- Create Logger ---
# We get the root logger so that all modules inherit this configuration
logger = logging.getLogger()
logger.setLevel(LOG_LEVEL)

# --- Create Console Handler ---
# This handler prints logs to the console
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(logging.Formatter(LOG_FORMAT))
logger.addHandler(console_handler)

# --- Create Rotating File Handler ---
# This handler writes logs to a file, rotating it daily.
# It will keep the last 7 days of logs.
file_handler = TimedRotatingFileHandler(
    filename=LOG_FILE,
    when="midnight",      # Rotate at midnight
    interval=1,           # Daily rotation
    backupCount=30,        # Keep 30 old log files
    encoding="utf-8"
)
file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
logger.addHandler(file_handler)