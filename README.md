# purgetools
Tools to walk scratch filesystem and manage their contents based on policy

## Purpose

Many HPC systems and others have large shared scratch/tmp spaces that have policies such as "delete all files not accessed in 60 days" etc. 
These tools are meant to help manage this process in a user informed way.  Unlike tmpcleaner or stock mpiFileUtils this will build a list per 
scratch directory and then from all those from a single scan sort them into per uid/user lists.

It will then optionally email the user a form letter with the location of their list of files to be purged.  
Finally it will optionally move the data to a staging area to then be deleted later or deleted in place.

## HowTo

Most tools take a `--dryrun` option showing what it will do without actually doing it

* Scan each directory under a parent directory using default settings
  * `buildlist.py /scratch/`
  * Creates `<scanident>-<directory>.cache` and `<scanident>-<directory>.txt` files
* Build per user lists for notification (optional notification TBD)
  * `userlist.py --scanident <scanident>`
* Stage or purge data
  * Move/Remove any `<scanident>-<directory>.cache`  files that should be excluded
  * `purgelist.py --days <days>  --scanident <scanident>`
  * Takes all files in the `<scanident>-<directory>.cache` files and checks if they are at least `--days <days>` last accessed.  If they are move to staging area
  

## Building

purgetools doesn't require any building and works on a stock centos7 python 3.6 environment.  It does depend on a patched version of mpiFileUtils

`build.sh` includes an example of building all the required versions and places them in the location.  You may need to update the modules required
You may wish to wrap this in spack (please do)

## TODO

 * Allow scanning just top level in one pass eg '/scratch/'  rather than each directory underneath (breaks path ignores)
 * User notification
  * Move sorted data to user visiable location and change ownership to the user and access to the file (metadata may be sensitive)
  * Email user form letter with location of their purge list
 * Stage to be deleted files 
  * Recreate path ignoreing any permissions
  * mv file (faster) preserving permissions
 * Purge list of files
  * Don't stage, just check age from list and blow away
  
 ## Limitations
 
 * It is not possible to exclude from purge by user, only by scratch path
