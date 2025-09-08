import pytest
import random
import string

import logging


@pytest.fixture
def logger_fixture():
    """return a logging.logger instance"""
    name = "".join(random.choices(string.ascii_letters + string.digits, k=10))
    return logging.getLogger(name)
