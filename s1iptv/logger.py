"""
File logging, matching the sibling apps' convention (Echo Audio Converter's
EAC_Log.txt, TorBox_Manager's TorBox_Manager_Log.txt) -- one plain-text log
file at the repo root, overwritten fresh each run.
"""

import logging
import os

from .paths import app_root

ROOT_DIR = app_root()
LOG_PATH = os.path.join(ROOT_DIR, 'S1_IPTV_Helper_Log.txt')

_logger = None


def setup_logging():
    global _logger
    logger = logging.getLogger("S1IptvHelper")
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()

    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")

    file_handler = logging.FileHandler(LOG_PATH, mode='w', encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    logger.info(f"Logging initialized: {LOG_PATH}")
    _logger = logger
    return logger


def get_logger():
    return _logger or setup_logging()
