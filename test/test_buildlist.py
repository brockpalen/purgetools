import argparse
import os
import pathlib
import sys
from contextlib import ExitStack as does_not_raise

import pytest

# needed to import functions in odd paths
sys.path.append(os.path.abspath("./"))

from buildlist import build_scanlist, parse_args

#  not checking scanident isn't required but default value
# @pytest.mark.parametrize(
#     "InvalidArgs",
#     [
#         (),  # scanident missing
#     ],
# )
# def test_missing_args(InvalidArgs):
#     """Check that required options are enforced."""
#     with pytest.raises(SystemExit) as e:
#         args = parse_args(InvalidArgs)
#         print(e)
#         assert isinstance(e.__context__, argparse.ArgumentError)
#     assert e.type == SystemExit


@pytest.mark.parametrize(
    "kwargs,count,exception",
    [
        ({}, 3, does_not_raise()),  # basic test
        ({"dontwalk": True}, 1, does_not_raise()),  # dontwalk should always return 1
        ({"excludes": ["a"]}, 2, does_not_raise()),  # basic test but exclude 'a'
        ({"excludes": ["e"]}, 3, pytest.raises(Exception)),  # bail of missing entry
        (
            {"excludes": ["e"], "ignoremissing": True},
            3,
            does_not_raise(),
        ),  # ignore missing entries
    ],
)
def test_build_scanlist(tmp_path, kwargs, count, exception):
    """Check number of directories found."""
    # make three top level directories and one second level
    a = tmp_path / "a"
    a.mkdir()
    b = tmp_path / "b"
    b.mkdir()
    c = tmp_path / "c"
    c.mkdir()
    d = c / "d"
    d.mkdir()  # make a directory deeper make sure not recurrsive

    with exception:
        roots = build_scanlist(tmp_path, **kwargs)
        assert len(roots) == count
