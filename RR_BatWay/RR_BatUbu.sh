#!/bin/bash
# invoke RR_BatUbu.py in Ubuntu under Wayland

# Workaround to delay autostart until System Tray has launched
# Increase if the Battery Icon does not show in the System Tray
sleep 5

RUNDIR=~/RedReactor/RR_BatWay/
RUNFILE=RR_BatUbu.py

cd $RUNDIR

if [ ! -f $RUNDIR$RUNFILE ]; then
	echo "** Unable to find " $RUNDIR$RUNFILE >> RR_BatWay.log
	exit 1
fi

nohup python3 $RUNFILE >& /dev/null &

# Write msg to journalctl
logger "RedReactor RR_BatUbu has started"
