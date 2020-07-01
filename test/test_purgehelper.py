import pytest, sys, os
from pprint import PrettyPrinter as pp
#needed to import functions in odd paths
sys.path.append(os.path.abspath('./'))

from purgehelper import parse_args

@pytest.mark.parametrize("InvalidArgs", [
                                 ('--days', '5'),
                                 ('--file', '/tmp/data'),
                                 ('--scanident', '1-1-999'),
                                 ('--scanident', '1-1-999', '--file', '/tmp/data'),
                                ])
def test_missing_args(InvalidArgs):
    with pytest.raises(SystemExit) as e:
         args = parse_args(InvalidArgs)
         assert isinstance(e.__context__, argparse.ArgumentError)
    assert e.type == SystemExit

@pytest.mark.parametrize("ValidArgs", [
                                 [('--file', '/tmp/data', '--days', '5', '--scanident', '1-1-999'),
                                  ('/tmp/data', '5', '1-1-999')]
                                ])
def test_valid_args(ValidArgs):
    args = parse_args(ValidArgs[0])
    assert args.file == ValidArgs[1][0]
    assert args.days == int(ValidArgs[1][1])
    assert args.scanident == ValidArgs[1][2]
