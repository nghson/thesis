#!/usr/bin/env python3
import os

PRE_FILE_VERSION = 3

FILE_DIR = os.path.dirname(__file__)
C_SRC_CODE_DIR = os.path.abspath(os.path.join(FILE_DIR, '..', '..', "planner/"))

STORAGE_LENGTH = 1000000000
