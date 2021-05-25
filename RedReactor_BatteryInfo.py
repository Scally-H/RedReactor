#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
*** RED REACTOR - Copyright (c) 2021
*** Author: Pascal Herczog

*** This code is designed for the RED REACTOR Raspberry Pi Battery Power Supply
*** Example code provided without warranty
*** Creates a BatteryMgr class with multi-threading for background monitoring

*** You may use/modify only for use with the RED REACTOR product
*** Filename: RedReactor_BatteryInfo.py
*** PythonVn: 3.8, 32-bit
*** Date: April 2021
"""

# Import libraries
from ina219 import INA219  # This controls the battery monitoring IC
from ina219 import DeviceRangeError  # Handle reading errors
import time  # Used to sleep between readings

# Constants
# RED REACTOR I2C address
I2C_ADDRESS = 0x40

# RED REACTOR Measurement Shunt (defined in Ohms)
SHUNT_OHMS = 0.05

# Battery threshold examples
BATTERY_VMAX = 4.2

# Any reading below this level triggers a shutdown
# Account for voltage drops due to current peaks
# Automatic shutdown occurs at 2.4v
BATTERY_VMIN = 2.9

# Set Current Measurement Range
MAX_EXPECTED_AMPS = 5.5

# Set the overcharge threshold at +1.5%
# When triggered, the voltage read will fluctuate but battery GND is disconnected
BATTERY_OVER = 4.2 * 1.015

print("RED REACTOR - Example code")
print("Battery Monitor: Shutdown at {:.2f}V".format(BATTERY_VMIN))

# ADC Default
# ADC*12BIT: 12 bit, conversion time 532us (default).

# Verify that RED REACTOR is attached, else abort
try:
    check_attached = INA219(SHUNT_OHMS, MAX_EXPECTED_AMPS)
    check_attached.configure(check_attached.RANGE_16V)
except OSError:
    print("RED REACTOR IS NOT Attached, exiting")
    exit(1)
else:
    print("RED REACTOR Attached")


class RedReactor:
    """Battery Monitor class, gets readings at user defined intervals"""

    def __init__(self, measure_interval):
        # measure_interval given in seconds

        print("RED REACTOR: Initialising battery manager")
        self.measure_interval = measure_interval
        print("RED REACTOR: Battery read interval set to {}s".format(self.measure_interval))

        # Initialise
        self.power = 0.0
        self.shuntv = 0.0
        # Set these to smooth out readings due to current spikes
        # Note readings will vary based on instantaneous load
        self.coefficients = (0.05, 0.15, 0.3, 0.5)

        # During start-up, exit immediately if first reading below BATTERY_VMIN
        # During operation, exit if average readings below BATTERY_VMIN
        self.shutdown = False

        # May be asserted by __main__ to force exit
        self.stop_reader = False

        # Set measurement config, ina class will optimise readings for resolution
        self.ina = INA219(SHUNT_OHMS, MAX_EXPECTED_AMPS)
        self.ina.configure(self.ina.RANGE_16V)

        # Read battery voltage
        # ina.voltage() - returns the bus voltage in V

        # For the following, an exception is thrown when result is out of ADC range
        # ina.supply_voltage() - returns the sum of bus supply voltage and shunt voltage
        # ina.current() - returns bus current in mA
        # ina.power() - returns the bus power consumption in mW
        # ina.shunt_voltage() - return shunt voltage value in mV

        # Note that the bus voltage is that on the load side of the shunt resistor
        # Voltage on the supply side = the bus voltage + shunt voltage

        # or use the supply_voltage() function.
        self.voltage = self.ina.voltage()
        # To know if charger is connected, measure current, check for out of range exception
        try:
            self.current = self.ina.current()
            print("RED REACTOR: Current (mA):", self.current)
            # Negative means charging, less than 10 means FULL but charger still connected
            if self.current < 0:
                self.is_charging = True
            else:
                self.is_charging = False
            if 0 > self.current < 10 and self.voltage < BATTERY_OVER:
                self.battery_full = True
            else:
                self.battery_full = False
        except DeviceRangeError as e:
            # Current out of device range with specified shunt resistor
            print("RED REACTOR:: Current Load out of measurement range\nError:", e)

        # Initialise history of 4 readings, last element is most recent
        self.history = [self.voltage, self.voltage, self.voltage, self.voltage]

        self.battery_charge = (self.voltage - BATTERY_VMIN) / (BATTERY_VMAX - BATTERY_VMIN)

        # Shutdown immediately if below VMIN without charger attached
        if self.voltage < BATTERY_VMIN and not self.is_charging:
            self.shutdown = True

    def stop_reading(self):
        self.stop_reader = True

    def battery_reader(self):
        """
        Runs indefinitely or until triggered to shut down or asked to stop_reading
        Should be called as a thread so user SW can run as well
        """

        while not self.stop_reader:

            # Read battery status
            # This is the sum of the bus voltage and shunt voltage
            self.voltage = self.ina.voltage()
            try:
                # Returns the bus current in milliamps (mA), or exception if exceed limit
                # Value is positive for discharge, negative for charging, or <10 if FULL and charger connected
                self.current = self.ina.current()
                if self.current < 0:
                    self.is_charging = True
                else:
                    self.is_charging = False
                # Include check for battery fault / overcharge condition
                if 0 < self.current < 10 and self.voltage < BATTERY_OVER:
                    self.battery_full = True
                else:
                    self.battery_full = False

                # Returns the bus power consumption in milliwatts (mW)
                self.power = self.ina.power()
                # Returns the shunt voltage in millivolts (mV)
                self.shuntv = self.ina.shunt_voltage()
            except DeviceRangeError as e:
                # Current out of device range with specified shunt resistor
                print("RED REACTOR: Current Load out of measurement range\nError:", e)
                # Max shunt voltage is 0.32v but at 0.05 Ohms this would be 6.4 Amps
                self.current = 6400.0
                self.power = self.voltage * abs(self.current)
                self.shuntv = 0.32
                # Given the exception, current is drawn from battery
                self.is_charging = False

            # Update read history, maintains last 4 readings incl. this one
            self.history.pop(0)
            self.history.append(self.voltage)

            # Calculate battery charge as percentage
            average_volt = (self.history[0] * self.coefficients[0]
                            + self.history[1] * self.coefficients[1]
                            + self.history[2] * self.coefficients[2]
                            + self.history[3] * self.coefficients[3])
            # Down to ~3v an 18650 discharge curve is more or less linear
            # If you choose to model this more accurately, account for current peaks
            self.battery_charge = (average_volt - BATTERY_VMIN) / (BATTERY_VMAX - BATTERY_VMIN)

            # STOP If average readings below VMIN
            if average_volt < BATTERY_VMIN:
                # Once set, it cannot be reset without a proper shutdown
                self.shutdown = True
                break

            # Put I2C device to sleep during reporting interval
            self.ina.sleep()
            # Check every second for user request to exit
            for waiting in range(0, self.measure_interval):
                time.sleep(1)
                if self.stop_reader:
                    break
            self.ina.wake()

        if self.shutdown:
            print("Battery Monitor: Exiting on battery voltage warning")
        else:
            print("Battery Monitor: Exiting on user request")


# Test code for running stand-alone and shows usage of functions
if __name__ == "__main__":

    """
    Example UI reading battery voltage and current at a reporting interval 
    No params gives 4.0 seconds interval, else specify as integer
    
    """

    import threading
    import sys

    if len(sys.argv) != 2:
        print("No time interval given, will measure every 4 seconds")
        report_interval = 4
    else:
        report_interval = int(sys.argv[1])
        print("Measuring every {} seconds".format(report_interval))

    # Initialise RedReactor and set measurement interval
    battery = RedReactor(report_interval)

    # Run battery monitoring in separate thread
    battery_reader_thread = threading.Thread(target=battery.battery_reader, name="BatteryMonitor")
    battery_reader_thread.start()

    try:
        while not battery.shutdown:
            time.sleep(report_interval)
            # An overcharge condition disconnects the battery GND terminal from the circuit
            # This is equivalent to no battery fitted, both give LED error indication
            if battery.voltage > BATTERY_OVER:
                print("Battery Error - No battery or overcharge detected. Reading {:.3f}v".format(battery.voltage))
                continue

            if battery.battery_full:
                print("Current Battery Status:"
                      " FULL, external power, Voltage {:.3f}v, Current {:.3f}mA".format(battery.voltage,
                                                                                              battery.current))
            else:
                print("Current Battery Status:"
                      " {}% - {}, "
                      "Voltage {:.3f}v, Current {:.3f}mA".format(min(int(battery.battery_charge * 100), 100),
                                                                 "Charging" if battery.is_charging else "No Mains",
                                                                 battery.voltage, battery.current))

            if battery.battery_charge < 0.1 and not battery.is_charging:
                print("UI: Battery Low Warning!")

        print("UI: Battery shutdown request detected")
    except KeyboardInterrupt:
        battery.stop_reading()
        print("UI: User shutdown request detected")
