#!/usr/bin/python3 -u

## -u is needed to avoid buffering stdout 

import argparse, pathlib, subprocess, configparser
import pprint 

# load config file settings
config = configparser.ConfigParser()
config.read(pathlib.Path(__file__).resolve().parent.joinpath('etc/buildlist.ini'))

#grab cli options
parser = argparse.ArgumentParser(description='Collect each user purge candidates into a single list')
parser.add_argument('--dryrun', help='Print list to scan and quit', action="store_true")
parser.add_argument('--scanident', help='Unique identifier for scan from buildlist.py ', type=str, required=True)

args = parser.parse_args()

pp = pprint.PrettyPrinter(indent=4)


# get list of all files matching 'scanident'
def get_dir_paths(path=pathlib.Path.cwd(),
                 scanident=args.scanident):
     

     return list(path.glob(f'{scanident}*.txt'))

# format of files being parsed
# -rw-rw---- bvansade glotzer 232.791 KB Nov 21 2019 15:48 /scratch/sglotzer_root/sglotzer/bvansade/peng-kai/cycles_poly/.ipynb_checkpoints/integrator_energy_replicates-checkpoint.ipynb

# get the user from the format
def get_user(line):
    if line is None:
      raise TypeError

    line = line.split()
    return line[1]

# 

paths = get_dir_paths(scanident=args.scanident)

pp.pprint(paths)

currentuser = ''

pathdict ={}

for path in paths:
   with path.open() as f:
      lines = f.readlines()
      for line in lines:
          lineuser = get_user(line)
          if lineuser in pathdict:
              pathdict[lineuser].write(line)
          else:
               user_log = pathlib.Path.cwd() / f"{args.scanident}-{lineuser}.purge.txt"
               g = user_log.open("a")
               pathdict[lineuser] = g
               g.write(line)
