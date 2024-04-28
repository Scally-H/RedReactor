#!/bin/bash
# Installer for redreactor linux kernel module

if [ `whoami` != root ]; then
  echo "Please run as root to install redreactor.ko kernel file"
  echo "Exiting"
  exit 1
fi

LINUXDRIVERS=/lib/modules/$(uname -r)/kernel/drivers/power/supply
REDREACTOR=redreactor.ko


echo "************************************************"
echo "Building and Installing redreactor kernel module"
echo "************************************************"


# Run all: target to create .ko file, then manual install because
# make install gives Warning: modules_install: missing 'System.map' file. Skipping depmod.
echo "Compiling redreactor Kernel Module"
make

# Check if .ko file created OK
if [ ! -f $REDREACTOR ]; then
	echo $REDREACTOR " not found, check for compile errors"
	echo "Exiting"
	exit 1
fi

# Check target folder exists
if [ ! -d $LINUXDRIVERS ]; then
	echo "** Unable to install redreactor.ko to " $LINUXDRIVERS
	echo "** Expected to find folder but does not exist"
	exit 1
fi

# Install redreactor.ko to target folder
echo "Copying $REDREACTOR to $LINUXDRIVERS"
cp $REDREACTOR $LINUXDRIVERS
if [ $? != 0 ]; then                   # last command: echo
   echo "Error copying file, exiting"
   exit 1
fi

# Add module name to /etc/modules file
if [ ! -f /etc/modules ]; then
	echo "/etc/modules not found, unable to add redreactor.ko"
	echo "Exiting"
	exit 1
fi

# Add redreactor to modules file if not already added
if ! grep -q redreactor /etc/modules
 then
	echo "Adding redreactor to /etc/modules file for auto-load on boot"
	cp /etc/modules /etc/modules.bck
	echo 'redreactor' | sudo tee -a /etc/modules
	if [ $? != 0 ]; then                   # last command: echo
	   echo "Error adding redreactor to /etc/modules"
	   echo "Exiting"
	   exit 1
	fi
fi

# All Done
echo "************************************************"
echo "Build and Install completed successfully.       "
echo "Or manually load the redreactor.ko file         "
echo "Use 'make clean' to remove temporary files      "
echo "Reboot to load redreactor kernel module         "
echo "************************************************"
