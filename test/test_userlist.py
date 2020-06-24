import pytest, sys, argparse, os

#needed to import functions in odd paths
sys.path.append(os.path.abspath('./'))
print(sys.path)
from userlist import get_user, parse_args
#########  input checking tests ##############

@pytest.mark.parametrize("input", ["hello-world_brock", "asdf124-jeff", "1234_world"])
def test_valid_scanident(input):
    """Test valid forms of --scanident <value>"""
    testargs = ["--scanident", input]
    args = parse_args(testargs)
    assert (args.scanident == input)

def test_missing_scanident():
    """--scanident is required input check if omitted the program exits at the right point"""
    # # this mess required because argparse will call sys.exit(2) rather than just raise
    # https://medium.com/python-pandemonium/testing-sys-exit-with-pytest-10c6e5f7726f
    testargs = ["--cachesize", "100"]
    with pytest.raises(SystemExit) as e:
         args = parse_args(testargs)
         assert isinstance(e.__context__, argparse.ArgumentError)
    assert e.type == SystemExit

@pytest.mark.parametrize("input", ["100", "10", "22"])
def test_valid_cachelimit(input):
    """Test valid forms of --cachelimit <value>"""
    testargs = ["--scanident", "test-ident", "--cachelimit", input]
    print(testargs)
    args = parse_args(testargs)
    assert (args.cachelimit == int(input))

@pytest.mark.parametrize("input", ["10a", "zxy", "%$#", "3.6"])
def test_invalid_cachelimit(input):
    """--cachelimit <input>  requires an int"""
    # # this mess required because argparse will call sys.exit(2) rather than just raise
    # https://medium.com/python-pandemonium/testing-sys-exit-with-pytest-10c6e5f7726f
    testargs = ["--scanident", "test-ident", "--cachesize", input]
    with pytest.raises(SystemExit) as e:
         args = parse_args(testargs)
         assert isinstance(e.__context__, argparse.ArgumentError)
    assert e.type == SystemExit


###### Stand alone function testing ########

@pytest.fixture
def dwalk_line():
    return "-rw-r--r-- msbritt support  18.000  B Aug 14 2019 17:04 /scratch/support_root/support/msbritt/testout"

def test_get_user(dwalk_line):
   # testargs = ["--scanident", "01-01-1970"]
   # print(dir(sys.argv))
   # monkeypatch.setattr(sys, 'argv', testargs)
   # print(dir(sys.argv))
    user = get_user(dwalk_line)
    assert (user == "msbritt")
    


