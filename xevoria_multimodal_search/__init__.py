# -*- coding: utf-8 -*-
import logging

_logger = logging.getLogger(__name__)

# Automatically raise Odoo's in-process memory and time limits on Windows so loading
# PyTorch / EmbeddingGemma 2 and bulk-indexing multiple products never triggers
# "Server memory limit reached" or "virtual real time limit (600s) reached".
try:
    from odoo.tools import config
    min_soft = 8 * 1024 * 1024 * 1024   # 8 GB
    min_hard = 10 * 1024 * 1024 * 1024  # 10 GB
    min_time = 7200                     # 7200s (2 hours) for bulk indexing

    if config.get("limit_memory_soft") and config["limit_memory_soft"] < min_soft:
        config["limit_memory_soft"] = min_soft
    if config.get("limit_memory_hard") and config["limit_memory_hard"] < min_hard:
        config["limit_memory_hard"] = min_hard
    if config.get("limit_time_real") and config["limit_time_real"] < min_time:
        config["limit_time_real"] = min_time
    if config.get("limit_time_cpu") and config["limit_time_cpu"] < min_time:
        config["limit_time_cpu"] = min_time
except Exception as e:
    _logger.debug("Resource limit adjustment notice: %s", e)

from . import models
from . import services
from . import controllers
