#!/usr/bin/python3 -u

## -u is needed to avoid buffering stdout 

import argparse, pathlib, subprocess, configparser
import pprint 
from datetime import datetime

# load config file settings
config = configparser.ConfigParser()
config.read(pathlib.Path(__file__).resolve().parent.joinpath('etc/buildlist.ini'))

#grab cli options
parser = argparse.ArgumentParser(description='Build file lists for groups of directories')
parser.add_argument('path', help='Path to scan', type=str)
parser.add_argument('--days', help='Number of days (Default 60)', type=int, default='60')
parser.add_argument('--np', help='Number of processors (Default 20)', type=int, default=20, metavar='N')
parser.add_argument('--progress', help='How often to print scan progress (Default 60)', type=int, metavar='S', default=60)
parser.add_argument('--dryrun', help='Print list to scan and quit', action="store_true")
parser.add_argument('--scanident', help='Unique identifier for scan to append to logs/files Default D-m-Y)', type=str, default=datetime.now().strftime("%d-%m-%Y"))

args = parser.parse_args()

pp = pprint.PrettyPrinter(indent=4)


# takes a comma seperated list of paths relative to PATH
# returns array of PathLib objects that exist
def check_path_exclude(path, excludelist=[], ignoremissing=False):
    resultlist = []
    for item in excludelist:
        candidate = ( path / item )
        if candidate.is_dir():
           resultlist.append(candidate)
        else:
           if not ignoremissing:
              raise Exception(f"{candidate} doesn't exist in {path}")

    return resultlist
       
# builds a set of paths to scan
# path is string of directory to walk for top level directories
def build_scanlist(path):
    path = pathlib.Path(path)
    if path.is_dir():
        print(f"Path {path.resolve()} exists")
    else:
        raise Exception(f"Path {args.path} does not exist")

    ex_paths = set(check_path_exclude(path, config['DEFAULT']['ignorepath'].split(',')))

    # can only scan directories
    sc_paths = set()
    for x in path.iterdir():
        if x.is_dir():
           sc_paths.add(x)

    return sc_paths - ex_paths

# scans actual filesystem and builds cache file and txt file
# path PathLib object to scan
# progress how often for mpiFileUtils to log progress
# np  number of MPI ranks to run on
# atime number of days and greater to scan for
# scanident  string to append to logs, defaults day-month-year
def scan_path(path, 
              scanident = datetime.now().strftime("%d-%m-%Y"),
              distribution = "size:0,1K,1M,100M,1G,1T",
              progress=int(60),
              np=int(20),
              atime=int(60),
              dryrun=False):
    

    # all settings for mpi
    args = [config['DEFAULT']['mpirunpath']]
    args.append('--allow-run-as-root')
    args.append('--oversubscribe')
    args += ["--mca", "io", f"{config['DEFAULT']['romio']}"]
    args += ["-np", f"{np}"]

    # add settings for dwalk, mpiFileUtils installed in <instdir>/install/bin/dwalk
    args.append(str(pathlib.Path(__file__).resolve().parent.joinpath("install/bin/dwalk")))
    args += ["--progress", f"{progress}"]
    args += ["--type", "f"]
    args += ["--atime", f"+{atime}"]
    args += ["--distribution", f"{distribution}"]
    args += ["--output", f"{scanident}-{path.name}.cache"]
    args.append(f"{path}")
    
    print(args)
    if (dryrun):
       print("--dryrun given not scanning, exiting")
       return

    subprocess.run(args, check=True)

    # dwalk will error if there are no files to sort, but sorting speeds building per user lists 
    # dwalk will also not write an output file if there are no entires so test if it exists if so sort it
    # this isn't as slow as expected as the sort is very fast,
    if pathlib.Path(f"{scanident}-{path.name}.cache").is_file():
        # cache file exists so sort and create sorted text version
        # no extra filters required 

        print("Purge Candidates found sorting")

        args = [config['DEFAULT']['mpirunpath']]
        args.append('--allow-run-as-root')
        args.append('--oversubscribe')
        args += ["--mca", "io", f"{config['DEFAULT']['romio']}"]
        args += ["-np", f"{np}"]
    
        # add settings for dwalk, mpiFileUtils installed in <instdir>/install/bin/dwalk
        args.append(str(pathlib.Path(__file__).resolve().parent.joinpath("install/bin/dwalk")))
        args += ["--progress", f"{progress}"]
        args += ["--type", "f"]
        args += ["--atime", f"+{atime}"]
        args += ["--distribution", f"{distribution}"]
        args += ["--sort", "user,name"]
        args += ["--input", f"{scanident}-{path.name}.cache"]
        args += ["--text-output", f"{scanident}-{path.name}.txt"]

        subprocess.run(args, check=True)

    else:
        print(f"No Purge candidates for {path.name}")



#########  MAIN PROGRM ########
scan_set = build_scanlist(args.path)

print("Will Scan Following List")
pp.pprint(scan_set)

for path in scan_set:
      scan_path(path,
                scanident = args.scanident,
                np = args.np,
                atime = args.days,
                progress = args.progress,
                dryrun=args.dryrun)
