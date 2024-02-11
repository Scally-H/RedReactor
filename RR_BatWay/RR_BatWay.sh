#!/bin/bash
# invoke RR_BatWay under Wayland on Pi Bookworm

# Workaround to delay autostart until System Tray has launched
# Increase if the Battery Icon does not show in the System Tray
sleep 5

RUNDIR=~/RedReactor/RR_BatWay/
RUNFILE=RR_BatWay.py

cd ~/RedReactor/RR_BatWay

if [ ! -f $RUNDIR$RUNFILE ]; then
	echo "** Unable to find " $RUNDIR$RUNFILE >> RR_BatWay.log
	exit 1
fi

nohup python3 RR_BatWay.py >& /dev/null &
