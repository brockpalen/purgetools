import argparse
import os
import sys

import pytest

# needed to import functions in odd paths
sys.path.append(os.path.abspath("./"))

from buildlist import parse_args

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
