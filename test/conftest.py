import pytest


@pytest.fixture
def data_dir(tmp_path):
    return tmp_path / "data"
