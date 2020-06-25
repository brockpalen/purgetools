import pytest, pathlib


@pytest.fixture
def path_test():
    """Path to the test directory"""
    p = pathlib.Path(__file__).parent.absolute()
    return p
