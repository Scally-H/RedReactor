#!/bin/bash
# Installer for RR_Driver system service

if [ `whoami` != root ]; then
  echo "Please run as root to install RR_Driver system service"
  echo "Exiting"
  exit 1
fi

SERVICE=/lib/systemd/system/
SERVICEFILE=RR_Driver.service
REDREACTOR=RR_Driver


echo "****************************************************"
echo "Building and Installing RR_Driver as system service "
echo "****************************************************"


# Compile driver without debug
echo "Compiling RR_Driver"
make

# Check if executable created OK
if [ ! -f ./build/$REDREACTOR ]; then
	echo "Compiled /build/$REDREACTOR not found, check for compile errors"
	echo "Exiting"
	exit 1
fi

# Copy RR_Driver.service to systemd folder
# Update home folder to users full path
echo "Updating and copying $SERVICEFILE to $SERVICE$SERVICEFILE"
sed "s|~|"/home/$(logname)"|g" $SERVICEFILE > $SERVICE$SERVICEFILE
if [ $? != 0 ]; then                   # last command: sed
   echo "Error copying file, exiting"
   exit 1
fi


# All Done
echo "************************************************"
echo "Build and Install completed successfully.       "
echo "Manually start driver using:                    "
echo "sudo systemctl start RR_Driver                  "
echo "Use 'make clean' to remove temporary files      "
echo "************************************************"
