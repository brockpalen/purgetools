import argparse
import logging
import os
import pathlib
import subprocess
import sys
from contextlib import ExitStack as does_not_raise
from unittest.mock import MagicMock

import pytest

# needed to import functions in odd paths
sys.path.append(os.path.abspath("./"))

from buildlist import build_scanlist, parse_args, scan_path

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
    "ValidArgs",
    [
        [("/tmp", "--scanident", "1-1-999"), ("/tmp", "1-1-999", False),],
        [("/tmp", "--scanident", "1-1-999", "--dryrun"), ("/tmp", "1-1-999", True),],
    ],
)
def test_valid_args(ValidArgs):
    args = parse_args(ValidArgs[0])
    assert args.path == ValidArgs[1][0]
    assert args.scanident == ValidArgs[1][1]
    assert args.dryrun == ValidArgs[1][2]


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


@pytest.mark.parametrize(
    "kwargs,calls",
    [({}, (2, 3)), ({"dryrun": True}, (0, 1)),],  # basic test  # dryrun never call
)
def test_scan_path(monkeypatch, tmp_path, kwargs, calls):
    # setup
    mock_subprocess = MagicMock()

    mock_Path = MagicMock()

    mock_parent = MagicMock()
    mock_parent.parent.joinpath.return_value = "i"

    mock_resolve = MagicMock()
    mock_resolve.resolve.return_value = mock_parent

    mock_is_file = MagicMock()
    mock_is_file.is_file.return_value = True

    mock_Path.side_effect = [mock_resolve, mock_is_file, mock_resolve]

    # run
    with monkeypatch.context() as m:
        m.setattr(pathlib, "Path", mock_Path)
        m.setattr(subprocess, "run", mock_subprocess)
        scan_path(path=tmp_path, **kwargs)

    # compare expected outcome
    logging.info(mock_subprocess.called_with)
    logging.info(mock_Path.called_with)
    assert mock_subprocess.call_count == calls[0]
    assert mock_Path.call_count == calls[1]
