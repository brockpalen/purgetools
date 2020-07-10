#!/usr/bin/python3 -u

## -u is needed to avoid buffering stdout

import argparse
import configparser
import datetime
import pathlib
import pprint
import subprocess
import sys
import time

# load config file settings
config = configparser.ConfigParser()
config.read(pathlib.Path(__file__).resolve().parent.joinpath("etc/buildlist.ini"))


def parse_args(args):
    # grab cli options
    parser = argparse.ArgumentParser(
        description="Final check and take options *** DO NOT INVOKE ALONE ***"
    )
    parser.add_argument(
        "--dryrun", help="Print what would do but dont do it", action="store_true"
    )
    parser.add_argument(
        "--days", help="Number of days to check st_atime", type=int, required=True
    )
    parser.add_argument(
        "--file", help="File to check and take action on", type=str, required=True
    )
    parser.add_argument(
        "--scanident",
        help="Unique identifier for scan from buildlist.py ",
        type=str,
        required=True,
    )

    args = parser.parse_args(args)
    return args


# print with a timestamp
def dtprint(string):
    now = datetime.datetime.fromtimestamp(time.time())
    s = now.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{s}] {string}")


# custom exceptions for PurgeObject
class PurgeError(Exception):
    """base class fro all custom exceptions for PurgeObject"""

    def __init__(self, PurgeObject, message):
        self.PurgeObject = PurgeObject
        self.message = message
        super().__init__(self.message)


class PurgeNotFileError(PurgeError):
    """exception class for files not existing"""

    pass


class PurgeDaysUnderError(PurgeError):
    """exception class when file is skiped for under age"""

    def __str__(self):
        try:
            atime = datetime.date.fromtimestamp(self.PurgeObject._stat.st_atime)
            today = datetime.date.today()
            s = f"st_atime: {atime} Today: {today} {self.PurgeObject._path} {self.message}"
        except Exception as e:
            print(type(e), e)
        return s


class PurgeObject:
    def __init__(
        self,
        path=False,  # (required) path to file in question
        days=False,  # (required) number of days old from TODAY required to take action on
        purge=False,  # don't move to stagepath, just blow it away NOT IMPLIMENTED
        stagepath=False,  # Path to move file to for staging
    ):
        """setup the path and rules for purge action (purge or stage)"""

        if stagepath and purge:
            raise PurgeError(
                self, "Cannot specify stagepath and purge at same time SAFETY"
            )
        if not days:
            raise PurgeError(self, "Must specify days for purge/stage")
        if (not stagepath) and (not purge):
            raise PurgeError(self, "Must provide purge or a path to stage data")

        # store the parameters
        # ok parameters are acceptable hit the filesystem
        self._check_valid(path)
        self._days = days
        self._purge = purge
        self._stagepath = stagepath

    def _check_valid(self, path):
        """Check if valid file and exists"""
        p = pathlib.Path(path)
        if p.is_file():
            self._path = p
            self._stat = p.stat()
        else:
            raise PurgeNotFileError(self, f"File {path} does not exist or file")

    def applyrules(self, dryrun=False):
        """apply the settings/rules to the file"""

        # check self._days rule
        today = datetime.date.today()
        delta = datetime.timedelta(days=self._days)
        delta = today - delta

        # if today - days > st_atime continue
        if self._stat.st_atime > time.mktime(delta.timetuple()):
            raise PurgeDaysUnderError(self, "file underage")

        # if file is purge remove (CAREFUL) else stage
        if self._purge:
            dtprint(f"Deleting {self._path}")
            # no op not implimented

        # stage, don't remove
        else:
            # mkpath in stragepath
            #  eg.   /scratch/sr/brockp/topurge.txt
            #  dest: /stagepath/scratch/sr/brockp/topurge.txt
            parent = self._path.parent  # get path part
            sd = pathlib.Path(self._stagepath) / parent.relative_to("/")
            sd.mkdir(parents=True, exist_ok=True)

            # move / rename file to new location
            target = sd / self._path.name
            dtprint(f"Staging {self._path}")
            self._path.rename(target)


if __name__ == "__main__":
    pp = pprint.PrettyPrinter(indent=4)
    args = parse_args(sys.argv[1:])

    # check it exists or exit
