#!/usr/bin/python3 -u

## -u is needed to avoid buffering stdout 

import argparse, pathlib, subprocess, configparser
import pprint, time
import sys

# load config file settings
config = configparser.ConfigParser()
config.read(pathlib.Path(__file__).resolve().parent.joinpath('etc/buildlist.ini'))

def parse_args(args):
    # grab cli options
    parser = argparse.ArgumentParser(description='Final check and take options *** DO NOT INVOKE ALONE ***')
    parser.add_argument('--dryrun', help='Print what would do but dont do it', action="store_true")
    parser.add_argument('--days', help='Number of days to check st_atime', type=int, required=True)
    parser.add_argument('--file', help='File to check and take action on',  type=str, required=True)
    parser.add_argument('--scanident', help='Unique identifier for scan from buildlist.py ', type=str, required=True)

    args = parser.parse_args(args)
    return args

class PurgeObject:
    def __init__(self, path=False):
        """setup the path"""
    def check_valid(self):
        """Check if valid file and exists"""
        
        if Path(path).is_file():
           return True
        else:
           raise Exception(f"File {path} does not exist")
    
    


if __name__ == "__main__":
    pp = pprint.PrettyPrinter(indent=4)
    args = parse_args(sys.argv[1:])

    # check it exists or exit
    
