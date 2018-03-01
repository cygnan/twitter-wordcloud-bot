#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging

logging.basicConfig(format=u"[%(filename)s:%(lineno)d] %(message)s")
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
