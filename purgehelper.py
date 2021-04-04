#!/usr/bin/python3 -u

## -u is needed to avoid buffering stdout

import argparse
import configparser
import datetime
import logging
import pathlib
import pprint
import pwd
import subprocess
import sys
import time

# load config file settings
config = configparser.ConfigParser()
config.read(pathlib.Path(__file__).resolve().parent.joinpath("etc/purgetools.ini"))


def parse_args(args):
    # grab cli options
    parser = argparse.ArgumentParser(
        description="Final check and take options *** DO NOT INVOKE ALONE ***"
    )
    parser.add_argument(
        "--dryrun", help="Print what would do but dont do it", action="store_true"
    )
    parser.add_argument(
        "--users-ignore",
        help="Comma list of usernames files to skip",
        type=str,
        default=False,
    )
    parser.add_argument(
        "--days", help="Number of days to check st_atime", type=int, required=True
    )
    parser.add_argument(
        "--file", help="File to check and take action on", type=str, required=True
    )
    parser.add_argument(
        "--purge", help="Don't stage, delete in place", action="store_true"
    )

    verbosity = parser.add_mutually_exclusive_group()
    verbosity.add_argument(
        "-v",
        "--verbose",
        help="Increase messages, including files as added",
        action="store_true",
    )
    verbosity.add_argument(
        "-q", "--quiet", help="Decrease messages", action="store_true"
    )

    args = parser.parse_args(args)
    return args


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
            atime = datetime.date.fromtimestamp(self.PurgeObject.stat.st_atime)
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
        userignore=False,  # array of usernames to ignore
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
        self.userignore = userignore

    def _check_valid(self, path):
        """Check if valid file and exists"""
        p = pathlib.Path(path)
        if p.is_file():
            self._path = p
            self.stat = p.stat()
        else:
            raise PurgeNotFileError(self, f"File {path} does not exist or file")

    def applyrules(self, dryrun=False, ignore_ctime=False):
        """apply the settings/rules to the file"""

        # check if file owned by a user to ignore if so skip everything else
        if self.userignore:  # there are users to ignore do extra lookup
            username = pwd.getpwuid(self.stat.st_uid).pw_name
            logging.debug(f"{self._path} owned by {username}")
            if username in self.userignore:
                # username found in ignorelist stop here
                logging.info(
                    f"Skipping {self._path} owned by {username} in ignore list"
                )
                return

        # check self._days rule
        today = datetime.date.today()
        delta = datetime.timedelta(days=self._days)
        delta = today - delta
        logging.debug(f"Today: {today} Delta: {delta}")

        cur_time = time.mktime(delta.timetuple())

        # if today - days > st_atime continue
        if self.stat.st_atime > cur_time:
            logging.debug(f"File Underage: {self._path} st_atime: {self.stat.st_atime}")
            raise PurgeDaysUnderError(self, "file underage atime")

        # if today - days > st_ctime continue
        if self.stat.st_ctime > cur_time and not ignore_ctime:
            logging.debug(f"File Underage: {self._path} st_ctime: {self.stat.st_ctime}")
            raise PurgeDaysUnderError(self, "file underage ctime")

        # if today - days > st_mtime continue
        if self.stat.st_mtime > cur_time:
            logging.debug(f"File Underage: {self._path} st_mtime: {self.stat.st_mtime}")
            raise PurgeDaysUnderError(self, "file underage mtime")

        # if file is purge remove (CAREFUL) else stage
        if self._purge:
            logging.info(f"Deleting {self._path}")

            if dryrun:
                logging.info("Dryrun requested skipping purge {self._path}")
            else:
                # actaully do it
                self._path.unlink()

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
            logging.info(f"Staging {self._path} to {target}")
            if dryrun:
                logging.info("Dryrun requested skipping stage/rename")
            else:
                # actaully do it
                self._path.rename(target)


if __name__ == "__main__":
    pp = pprint.PrettyPrinter(indent=4)
    args = parse_args(sys.argv[1:])

    if args.quiet:
        level = logging.WARNING
    elif args.verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO

    logging.basicConfig(format="%(asctime)s %(levelname)s %(message)s", level=level)

    po_args = {
        "path": args.file,
        "days": args.days,
        "userignore": args.users_ignore.split(","),
    }

    # set if were purging or staging
    if args.purge:
        po_args["purge"] = True
    else:
        # staging
        po_args["stagepath"] = config["purgehelper"]["stagepath"]

    try:
        # Run the actual purge / stage
        po = PurgeObject(**po_args)
        po.applyrules(dryrun=args.dryrun)

    except PurgeNotFileError as e:
        # do stuff here with files that don't exist
        logging.info(f"{e}")
    except PurgeDaysUnderError as e:
        # do stuff here with files that are now under age
        logging.info(f"{e}")
