#!/usr/bin/python3 -u

## -u is needed to avoid buffering stdout

import argparse
import configparser
import logging
import pathlib
import pprint
import pwd
import re
import shutil
import smtplib
import stat
import sys
from collections import OrderedDict
from datetime import datetime
from email.headerregistry import Address
from email.message import EmailMessage
from string import Template

# load config file settings
config = configparser.ConfigParser()
config.read(pathlib.Path(__file__).resolve().parent.joinpath("etc/purgetools.ini"))


def parse_args(args):
    # grab cli options
    parser = argparse.ArgumentParser(
        description="Collect each user purge candidates into a single list"
    )
    parser.add_argument(
        "--dryrun", help="Print list to scan and quit", action="store_true"
    )
    parser.add_argument(
        "--scanident",
        help="Unique identifier for scan from buildlist.py ",
        type=str,
        required=True,
    )
    parser.add_argument(
        "--cachelimit", help="Number of file hanels to hold open", type=int, default=100
    )
    parser.add_argument(
        "--email", help="Email users a notice of their purge list", action="store_true"
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


# get list of all files matching 'scanident'
def get_dir_paths(path=pathlib.Path.cwd(), scanident=None):

    return list(path.glob(f"{scanident}*.txt"))


# format of files being parsed
# -rw-rw---- bvansade glotzer 232.791 KB Nov 21 2019 15:48 /scratch/sglotzer_root/sglotzer/bvansade/peng-kai/cycles_poly/.ipynb_checkpoints/integrator_energy_replicates-checkpoint.ipynb

# get the user from the format
def get_user(line):
    if line is None:
        raise TypeError

    line = line.split()
    return line[1]


#


# class that actually takes the strings and writes them to files
class UserSort:
    # cachelimit is number of open files to hold open
    # if you get to many open files lower this value default=100
    def __init__(self, scanident, cachelimit=100):
        self._handles = OrderedDict()
        self._cachelimit = cachelimit
        self._scanident = scanident

    # returns handle if exists in _handles or creates a new one push end of list
    # if _handles.count() = cachelimit  pop front of list
    def _gethandle(self, lineuser):
        if lineuser in self._handles:
            return self._handles[lineuser]

        else:
            # check if we are at cached limit
            if len(self._handles) >= self._cachelimit:
                # already have maxed cached handles remove the first one created
                # this is overly simple and does not actaully do remove last recently accessed
                self._handles.popitem(last=False)

            # go ahead and create handle
            user_log = pathlib.Path.cwd() / f"{self._scanident}-{lineuser}.purge.txt"
            g = user_log.open("a")
            self._handles[lineuser] = g
            return self._handles[lineuser]

    # take user and line check if already have cache in
    # _handles if so write otherwise create a new one
    def writeline(self, lineuser, line):
        handle = self._gethandle(lineuser)
        handle.write(line)

    def sort(self, paths):
        for path in paths:
            with path.open() as f:
                lines = f.readlines()
                for line in lines:
                    lineuser = get_user(line)
                    self.writeline(lineuser, line)


# class that notifies user by
#  1. Copy the *purge* files to a public location
#  2. Set the permissions/ownership of the copy
#  3. Email a template to the user with location
class UserNotify:
    def __init__(self, email=False, notifypath=False, mode=0o400, template=False):
        self._mode = mode  # mode to set the file to
        self._notifypath = notifypath  # path to put the notices in

        # check requireds
        if not notifypath:
            raise Exception("no path given for notification user logs")

    def copy(self):
        """
        Copy per user purge lists to public location and set permissions.

        For each per user purge list ( *.purge.txt )
        Copy them to notifypath
        Change ownership to mode
        Set owner to user

        return tuple (username, path to file)
        """
        lists = pathlib.Path.cwd().glob("*.purge.txt")
        for s_file in lists:
            name = s_file.name
            d_file = pathlib.Path(f"{self._notifypath}") / name
            logging.debug(f"Copying {s_file} to {d_file}")
            shutil.copy(s_file, d_file)
            # set owner
            username = self._getuser(d_file)

            try:
                logging.debug(f"Change {d_file} owner to {username}")
                shutil.chown(d_file, user=username)
            except LookupError as e:  # username not found
                logging.warning(f"{e}")

            # set permissions
            logging.debug(f"Set permissions on {d_file} to {stat.filemode(self._mode)}")
            d_file.chmod(self._mode)

            yield username, d_file

    def _getuser(self, d_file):
        """Get username from purge list filename"""
        name = d_file.name
        # format it {ident}-{user}.purge.txt
        match = re.match(r".+-(\w+).purge.txt", name)
        if match:
            return match.group(1)
        else:
            raise Exception(f"Problem with parsing user in {name}")


class EmailFromTemplate:
    """
    Email a single entity using a template.

    """

    def __init__(self, template=False):
        """
        Build email template

        template pathlib path to template
        """
        self.template = template

    def compose(
        self, to_user=False, from_user=False, subject=False, reply_to=False, data=False
    ):
        """
        Compose the actual message.

        to_user Tuple ("Display Name", "user@domain.com")
        from_user Tuple ("Display Name", "user@domain.com")
        reply_to Tuple ("Display Name", "user@domain.com")   Optional
        subject str  Subjet Line
        data dict Dict of substitution values for the Template
        """
        self.msg = EmailMessage()
        logging.debug(f"Subject set to: {subject}")
        self.msg["Subject"] = subject
        from_composed = Address(display_name=from_user[0], addr_spec=from_user[1])
        logging.debug(f"Email From: {from_composed}")
        self.msg["From"] = from_composed
        to_composed = Address(display_name=to_user[0], addr_spec=to_user[1])
        logging.debug(f"Email to: {to_composed}")
        self.msg["To"] = to_composed

        if reply_to:
            reply_to_composed = Address(display_name=reply_to[0], addr_spec=reply_to[1])
            logging.debug(f"Reply to: {reply_to_composed}")
            self.msg["reply-to"] = reply_to_composed

        with open(self.template) as f:
            tpl = Template(f.read())
            self.msg.set_content(tpl.safe_substitute(**data))

    def as_string(self):
        """return composed message as string."""
        return self.msg.as_string()

    def send(self):
        """Send actual message."""
        with smtplib.SMTP("localhost") as s:
            s.send_message(self.msg)


def email_purgelist(path=False, username=False):
    """
    Email the user a template where they can find their data.

    path pathlib purge list location on cluster
    username str username on the system to look up needed informatoin
    """

    # read all values from config file
    email_template = config["userlist"]["emailtemplate"]
    cluster = config["userlist"]["cluster"]
    email_domain = config["userlist"]["emaildomain"]
    from_user = config["userlist"]["fromuser"]
    from_email = config["userlist"]["fromemail"]
    email_subject = config["userlist"]["emailsubject"]
    policy_link = config["userlist"]["policylink"]

    today = datetime.now().strftime("%B %-d, %Y")

    # get users common name
    common_name = pwd.getpwnam(username).pw_gecos

    # setup template subsitution dict
    sub_data = {
        "path": path,
        "username": username,
        "commonname": common_name,
        "cluster": cluster,
        "policylink": policy_link,
        "today": today,
    }

    # email setup
    email = EmailFromTemplate(
        template=pathlib.Path(__file__).resolve().parent / "etc" / email_template
    )
    to_user = (common_name, f"{username}@{email_domain}")
    from_user = (from_user, from_email)
    subject = Template(email_subject).safe_substitute(**sub_data)
    email.compose(to_user=to_user, from_user=from_user, subject=subject, data=sub_data)
    logging.debug(f"Composed message \n {email.as_string()}")

    # send
    if args.email:
        # send it
        logging.debug(f"Sending message for {username}")
        email.send()


if __name__ == "__main__":
    pp = pprint.PrettyPrinter(indent=4)
    args = parse_args(sys.argv[1:])

    if args.quiet:
        logging.basicConfig(level=logging.WARNING)
    elif args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    paths = get_dir_paths(scanident=args.scanident)

    pp.pprint(paths)

    if args.dryrun:
        print("--dryrun given exiting")
        exit(0)

    currentuser = ""

    # sort + merge per path scans into per user lists
    sorter = UserSort(cachelimit=args.cachelimit, scanident=args.scanident)
    sorter.sort(paths)

    # notify the user of the location of their data
    notifier = UserNotify(
        notifypath=config["userlist"]["notifypath"],
        mode=int(config["userlist"]["mode"], 8),
    )
    for username, path in notifier.copy():
        logging.debug(f"User Purge list: {path}")
        email_purgelist(path=path, username=username)
