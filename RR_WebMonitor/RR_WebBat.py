#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
*** RED REACTOR - Copyright (c) 2021
*** Author: Pascal Herczog

*** This code is designed for the RED REACTOR Raspberry Pi Battery Power Supply
*** Example code provided without warranty
*** Simple configuration for Red Reactor battery monitoring in RR_WebMonitor

*** You may use/modify only for use with the RED REACTOR product
*** Filename: RR_WebBat.py
*** PythonVn: 3.8, 32-bit
*** Date: April 2021
"""

# Import libraries
from ina219 import INA219  # This controls the battery monitoring IC
from ina219 import DeviceRangeError  # Handle reading errors

# Constants
# RED REACTOR I2C address
I2C_ADDRESS = 0x40

# RED REACTOR Measurement Shunt (defined in Ohms)
SHUNT_OHMS = 0.05

# Battery threshold examples, adjusted for charge/discharge offsets
BATTERY_VMAX = 4.2

# Automatic shutdown occurs at 2.4v
BATTERY_VMIN = 2.9

# Set Current Measurement Range
MAX_EXPECTED_AMPS = 5.5

# Set the overcharge threshold at +1.5%
# When triggered, the voltage read will fluctuate but battery GND is disconnected
BATTERY_OVER = 4.2 * 1.015
BATTERY_CHRG = 0.01
BATTERY_DCHG = 0.05

# ADC Default
# ADC*12BIT: 12 bit, conversion time 532us (default).

# Verify that RED REACTOR is attached, else abort
try:
    # Added busnum to ensure correct I2C bus used
    check_attached = INA219(SHUNT_OHMS, MAX_EXPECTED_AMPS, busnum=1)
    check_attached.configure(check_attached.RANGE_16V)
except OSError:
    print("Unable to access RED REACTOR, exiting")
    raise RuntimeError("Unable to access RED REACTOR")
else:
    print("RED REACTOR : Attached")


# Refactored from RedReactor class to simplify integration into RR_WebMonitor
class RRWebBat:
    """Battery Monitor class, simple reading of battery status for web monitoring"""

    def __init__(self):
        # Initialise

        # Set these to smooth out readings due to current spikes
        # Note readings will vary based on instantaneous load
        self.coefficients = (0.05, 0.15, 0.3, 0.5)

        # During start-up, exit immediately if first reading below BATTERY_VMIN
        # During operation, exit if average readings below BATTERY_VMIN
        self.shutdown = False

        # Set measurement config, ina class will optimise readings for resolution
        # Added busnum to ensure correct I2C bus used
        self.ina = INA219(SHUNT_OHMS, MAX_EXPECTED_AMPS, busnum=1)
        self.ina.configure(self.ina.RANGE_16V)

        # Initialise readings
        self.voltage = self.ina.voltage()
        self.current = 0
        self.battery_charge = 100
        # [FULL, CHARGING, DISCHARGING, FAULT]
        self.battery_status = "FULL"

        # Initialise history of 4 readings, last element is most recent
        self.history = [self.voltage, self.voltage, self.voltage, self.voltage]

        # Get actual readings
        self.get_battery()

        # Shutdown immediately if below VMIN without charger attached
        if self.voltage < BATTERY_VMIN and self.battery_status != "CHARGING":
            self.shutdown = True

    def get_battery(self):
        """
        Simple function to track battery status
        """

        # Wake up INA219 IC
        self.ina.wake()

        # This is the sum of the bus voltage and shunt voltage
        self.voltage = self.ina.voltage()
        try:
            # Returns the bus current in milliamps (mA), or exception if exceed limit
            # Value is positive for discharge, negative for charging, or <10 if FULL and charger connected
            self.current = self.ina.current()
            if self.current < 0:
                self.battery_status = "CHARGING"
            elif self.current < 10:
                # Check if there is a battery fault
                # Adjusted for production Battery Management IC, detect error if voltage changes > 0.01 when FULL
                if self.voltage > BATTERY_OVER or \
                        self.battery_status in ["FULL", "FAULT"] and abs(self.voltage - self.history[-1]) > 0.01:
                    print("RED REACTOR : BATTERY ERROR")
                    self.battery_status = "FAULT"
                    self.battery_charge = 100
                else:
                    self.battery_status = "FULL"
            else:
                self.battery_status = "DISCHARGING"

        except DeviceRangeError as e:
            # Current out of device range with specified shunt resistor
            print("RED REACTOR : Current Load out of measurement range\nError:", e)
            # Max shunt voltage is 0.32v but at 0.05 Ohms this would be 6.4 Amps
            self.current = 6400.0
            self.battery_status = "FAULT"
            self.battery_charge = 100

        # Update read history, maintains last 4 readings incl. this one
        self.history.pop(0)
        self.history.append(self.voltage)

        # Calculate battery charge as percentage
        average_volt = (self.history[0] * self.coefficients[0]
                        + self.history[1] * self.coefficients[1]
                        + self.history[2] * self.coefficients[2]
                        + self.history[3] * self.coefficients[3])

        # Set Charge Level (except for FAULT)
        if self.battery_status == "CHARGING":
            # Adjust charge level w.r.t. charging state
            self.battery_charge = \
                min(100, int(((average_volt - BATTERY_VMIN) / (BATTERY_VMAX + BATTERY_CHRG - BATTERY_VMIN)) * 100))
        elif self.battery_status in ['DISCHARGING', 'FULL']:
            self.battery_charge = \
                min(100, int(((average_volt - BATTERY_VMIN) / (BATTERY_VMAX - BATTERY_DCHG - BATTERY_VMIN)) * 100))
        # If system goes below VMIN, show 0%
        if self.battery_charge < 0:
            self.battery_charge = 0

        # Assert shutdown status if average readings below BATTERY_VMIN
        if average_volt < BATTERY_VMIN:
            # Once set, it cannot be reset without a proper shutdown
            print("RED REACTOR : LOW battery voltage warning")
            self.shutdown = True

        # Put INA219 IC device to sleep until next read request
        self.ina.sleep()


# Test code for running stand-alone and shows usage of functions
if __name__ == "__main__":
    """
    Test RRWebBat
    Can use this to create CSV log of battery performance
    
    """

    import time
    import sys

    if len(sys.argv) != 2:
        print("No time interval given, will measure every 5 seconds")
        report_interval = 5
    else:
        report_interval = int(sys.argv[1])
        print("Measuring every {} seconds".format(report_interval))

    # Initialise RedReactor and set measurement interval
    battery = RRWebBat()

    with open("RR_WebBat.log", "w") as log_file:
        log_file.write("Volts,Current,Charge,Status\n")
        print("Volts   Current Charge Status\n" + "*" * 36)
        try:
            while not battery.shutdown or battery.battery_status == "FAULT":
                battery.get_battery()
                log_msg = "{:.3f}, {:7.2f}, {:4}%, {}\n".format(battery.voltage,
                                                                battery.current,
                                                                battery.battery_charge,
                                                                battery.battery_status
                                                                )
                log_file.write(log_msg)
                print(log_msg)
                time.sleep(report_interval)

            if battery.shutdown:
                print("Battery SHUTDOWN Required!")
            if battery.battery_status == "FAULT":
                print("Battery ERROR Detected")
        except KeyboardInterrupt:
            print("UI: User shutdown request detected")

    print("Exiting RRWebBat Test")
