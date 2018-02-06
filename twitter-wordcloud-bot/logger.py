#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import os

logging.basicConfig(format=u"[%(filename)s:%(lineno)d] %(message)s")
logger = logging.getLogger(
    os.path.splitext(os.path.basename(__file__))[0].decode("utf-8")
)
logger.setLevel(logging.DEBUG)
