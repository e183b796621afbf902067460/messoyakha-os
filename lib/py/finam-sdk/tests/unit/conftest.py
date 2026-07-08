import os

import pytest


@pytest.fixture
def secret() -> str:
    return os.environ["FINAM_API_SECRET"]
