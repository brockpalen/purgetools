#!/bin/bash

# Simple wrapper for calling purgehelper currentlya
# USAGE:  runpurge.sh <scanident>

# Setup

USERIGNORE=brockp,root

DFIND=/scratch/support_root/support/brockp/purge/install/bin/dfind
MPIRUN=/sw/arcts/centos7/gcc_4_8_5/openmpi/3.1.4/bin/mpirun
NP=32
PURGEHELPER=/scratch/support_root/support/brockp/purge/dist/purgehelper


# exit if no arguments given
if [ $# -eq 0 ]; then
    echo "No <scanident> provided"
    echo "Usage: runpurge.sh <scanident>"
    exit 1
fi

LIST=$(ls ${1}*.cache)

echo "Will process $LIST:"

echo ""

read -n 1 -s -r -p "Press any key to continue"

echo ""

for x in $LIST
do

echo $x

time \
$MPIRUN -np 32 \
	--oversubscribe \
	--allow-run-as-root \
	$DFIND --exec $PURGEHELPER --purge --verbose --days 60  --users-ignore $USERIGNORE --file {} \; --input $x  > ${x}.purge.log 2>&1

done
