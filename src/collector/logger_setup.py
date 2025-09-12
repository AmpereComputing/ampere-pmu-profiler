# Copyright (c) 2025, Ampere Computing LLC.
#
# SPDX-License-Identifier: BSD-3-Clause

import logging


def setup_logger(
    log_level: str = "INFO", log_filename: str = "app.log"
) -> logging.Logger:
    logger = logging.getLogger("app")
    logger.setLevel(log_level.upper())
    # Remove any existing handlers
    if logger.hasHandlers():
        logger.handlers.clear()
    logger.propagate = False
    formatter = logging.Formatter("[%(asctime)s] %(levelname)s - %(message)s")
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    file_handler = logging.FileHandler(log_filename)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger
