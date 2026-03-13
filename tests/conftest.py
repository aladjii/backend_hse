import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import pytest
from fastapi.testclient import TestClient
from main import app


@pytest.fixture
def client():

    app.state.db_pool = None 

    return TestClient(app)