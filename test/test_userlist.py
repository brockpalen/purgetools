import argparse
import filecmp
import logging
import os
import shutil
import smtplib
import stat
import sys
from pprint import PrettyPrinter as pp
from unittest.mock import MagicMock

import pytest

# needed to import functions in odd paths
sys.path.append(os.path.abspath("./"))

from userlist import (
    EmailFromTemplate,
    UserNotify,
    UserSort,
    get_dir_paths,
    get_user,
    parse_args,
)

#########  input checking tests ##############


@pytest.mark.parametrize("input", ["hello-world_brock", "asdf124-jeff", "1234_world"])
def test_valid_scanident(input):
    """Test valid forms of --scanident <value>"""
    testargs = ["--scanident", input]
    args = parse_args(testargs)
    assert args.scanident == input


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
    assert args.cachelimit == int(input)


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
    assert user == "msbritt"


# create test list of scanident files
@pytest.fixture
def scanidents_txt(tmp_path):
    """ create a number of test 'txt' files to scan"""
    suffixs = ["a", "b", "c", "d"]
    for f in suffixs:
        p = tmp_path / f"testident-{f}.txt"
        p.touch()

    return tmp_path


def test_get_dir_paths(scanidents_txt):
    """make sure get_dir_paths() doesn't miss any entries"""
    print(dir(scanidents_txt))
    for x in scanidents_txt.iterdir():
        print(x.name)
    assert 4 == len(get_dir_paths(scanidents_txt, "testident"))


@pytest.fixture
def example_path(tmp_path, path_test):
    """stage example data for UserSort()"""
    tdata = path_test / "data" / "ident-example-support.txt"
    ddata = tmp_path / "ident-example-support.txt"

    shutil.copy(tdata, ddata)

    return tmp_path


def test_UserSort(example_path, path_test):
    """pass example data through UserSort and compare output files"""
    os.chdir(example_path)
    sorter = UserSort(scanident="ident-example")
    sorter.sort([example_path / "ident-example-support.txt"])

    # delete to force flushing of buffers
    del sorter

    # should produce three purge lists
    exptected_purge = [
        "ident-example-bennet.purge.txt",
        "ident-example-mmiranda.purge.txt",
        "ident-example-msbritt.purge.txt",
    ]

    # should be exactly 4 files after running
    assert len(list(example_path.glob("*"))) == 4

    # compare the contents
    for x in exptected_purge:
        p1 = example_path / str(x)
        p2 = path_test / "data" / str(x)
        print(p1)
        print(p2)
        assert filecmp.cmp(p1, p2, shallow=False)


def test_UserNotify_nopath():
    """Check throws on required inputs for UserNotify"""
    with pytest.raises(BaseException):
        n = UserNotify()


def test_UserNotify(tmp_path, path_test, monkeypatch):
    """copy the purge"""

    # replace shutil.chown() with a check for the expected users
    # this keeps from the users being actually needed
    def mockreturn(*args, **kwargs):
        # check that the user passed is in the list
        users = ["msbritt", "bennet", "mmiranda"]
        if kwargs["user"] in users:
            return True

        else:
            raise Exception("invalid user passwd to shutil.chown")

    monkeypatch.setattr(shutil, "chown", mockreturn)

    os.chdir(path_test / "data")
    n = UserNotify(notifypath=tmp_path)
    n.copy()
    result = tmp_path.glob("*")
    assert len(list(result)) == 3  # should be 3 files when complete
    for f in tmp_path.glob("*"):
        assert (
            stat.filemode(f.stat().st_mode) == "-r--------"
        )  # default should be readable only by the user


def test_EmailFromTemplate(tmp_path, monkeypatch):
    # setup test data template
    s_template = """this is my junk template $hello and $world"""
    d_template = tmp_path / "test.tpl"
    with d_template.open("w") as template:
        template.write(s_template)

    composed = """Subject: my subject
From: hpc systems <arcts-support@umich.edu>
To: Brock Palen <brockp@umich.edu>
reply-to: ARC-TS Support <arcts-support@umich.edu>
Content-Type: text/plain; charset="utf-8"
Content-Transfer-Encoding: 7bit
MIME-Version: 1.0

this is my junk template world and hello
"""

    # replace  SMTP.send_message()
    smtp = MagicMock(spec=smtplib.SMTP)
    monkeypatch.setattr(smtplib.SMTP, "send_message", smtp)

    email = EmailFromTemplate(template=d_template)
    to_user = ("Brock Palen", "brockp@umich.edu")
    from_user = ("hpc systems", "arcts-support@umich.edu")
    reply_to = ("ARC-TS Support", "arcts-support@umich.edu")
    email.send(
        to_user=to_user,
        from_user=from_user,
        reply_to=reply_to,
        subject="my subject",
        data={"hello": "world", "world": "hello"},
    )
    # grab composed message as string and compare
    message = smtp.call_args[0][0].as_string()
    logging.debug(f"Composed message: {message}")
    # compare message passed to smtplib with expected
    assert message == composed
