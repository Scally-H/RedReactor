#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
*** RED REACTOR - Copyright (c) 2024
*** Author: Pascal Herczog

*** This code is designed for the RED REACTOR Raspberry Pi Battery Power Supply
*** Example code provided without warranty
*** Provides Battery Monitoring class for RR_BatWay

*** You may use/modify only for use with the RED REACTOR product
*** Filename: RR_WebMon.py
*** PythonVn: >=3.8
*** Date: February 2024
"""

# Import libraries
try:
    from ina219 import INA219, DeviceRangeError
except ModuleNotFoundError:
    from ina219_pc import INA219, DeviceRangeError

# Constants
# RED REACTOR I2C address, do not change
I2C_ADDRESS = 0x40

# RED REACTOR Measurement Shunt (defined in Ohms), do not change
SHUNT_OHMS = 0.05

# Battery Charge level, do not change
BATTERY_VMAX = 4.2

# Forced poweroff occurs at 2.4v
# Set this as desired Safe Shutdown voltage
BATTERY_VMIN = 2.9

# Set Current Measurement Range, do not change
MAX_EXPECTED_AMPS = 5.5

# Set the overcharge threshold at +1.5%
# When triggered, the voltage read will fluctuate but battery GND is disconnected
BATTERY_OVER = 4.2 * 1.015
# Adjust Battery charge 100% level before end of charge cycle
BATTERY_CHRG = 0.01
# Adjust Battery charge 100% level after end of charge cycle
BATTERY_DCHG = 0.05

# ADC Default
# ADC*12BIT: 12 bit, conversion time 532us (default).


class RRBatMon:
    """Battery Monitor class, simple reading of battery status for taskbar icon"""

    def __init__(self, averaging=5):
        # Initialise battery data
        # Averaging smooths out instantaneous peaks
        self.averaging_count = averaging

        self.voltage = 0
        self.voltage_av = 0
        self.current = 0
        self.current_av = 0
        self.battery_charge = 0
        # [FULL, CHARGING, DISCHARGING, FAULT]
        self.battery_status = "FULL"

        # Verify that RED REACTOR is attached, else set ERROR
        try:
            # Set measurement config, ina class will optimise readings for resolution
            # Added busnum to ensure correct I2C bus used
            self.ina = INA219(SHUNT_OHMS, MAX_EXPECTED_AMPS, busnum=1)
            self.ina.configure(self.ina.RANGE_16V)
        except OSError:
            self.battery_status = "ERROR"

        # Set averaging ratios, e.g., [1] / [0.5, 0.5] / [0.25, 0.25, 0.5] etc
        # Note last element is most recent
        self.coefficients = []
        if self.averaging_count == 1:
            self.coefficients = [1]
        else:
            self.coefficients = [0.5]
            for index in range(self.averaging_count-2):
                # small list so use insert
                self.coefficients.insert(0, self.coefficients[0]/2)
            self.coefficients.insert(0, 1-sum(self.coefficients))

        # During start-up, exit immediately if first reading below BATTERY_VMIN
        # During operation, exit if average readings below BATTERY_VMIN
        self.shutdown = False

        if self.battery_status != "ERROR":
            # Initialise readings
            self.voltage = self.ina.voltage()
            # Initialise history of n readings, last element is most recent
            self.v_hist = [self.voltage] * self.averaging_count
            self.a_hist = [0] * self.averaging_count

            # Get actual readings
            self.get_battery()

            # Shutdown immediately if below VMIN without charger attached
            if self.voltage < BATTERY_VMIN and self.battery_status != "CHARGING":
                self.shutdown = True
        else:
            # exit due to system error to trigger application quit
            raise RuntimeError("Unable to access RED REACTOR")

    def get_battery(self):
        """
        Simple function to read battery status
        """
        # Wake up INA219 IC
        self.ina.wake()
        try:
            # This is the sum of the bus voltage and shunt voltage
            self.voltage = self.ina.voltage()
            # mA is positive for discharge, negative for charging, or <10 if FULL and charger connected
            self.current = self.ina.current()
            if self.current < 0:
                self.battery_status = "CHARGING"
            elif self.current < 10:
                # Check if there is a battery fault
                # Adjusted for production Battery Management IC, detect error if voltage changes > 0.025 when FULL
                if self.voltage > BATTERY_OVER or \
                        self.battery_status in ["FULL", "FAULT"] and abs(self.voltage - self.v_hist[-1]) > 0.025:
                    # print("RED REACTOR : BATTERY FAULT", self.voltage, self.v_hist[-1], self.ina.current())
                    self.battery_status = "FAULT"
                    self.battery_charge = 100
                else:
                    self.battery_status = "FULL"
            else:
                self.battery_status = "DISCHARGING"

        except DeviceRangeError as read_error:
            # Current out of device range with specified shunt resistor
            # print("RED REACTOR : Current Load out of measurement range\nError:", read_error)
            # Max shunt voltage is 0.32v but at 0.05 Ohms this would be 6.4 Amps
            self.current = 6400.0
            self.battery_status = "FAULT"
            self.battery_charge = 100

        # Update read history, maintains last 4 readings incl. this one
        self.v_hist.pop(0)
        self.v_hist.append(self.voltage)
        self.a_hist.pop(0)
        self.a_hist.append(self.current)

        # Calculate battery charge as percentage, using averaged voltage
        self.voltage_av = sum([self.coefficients[i] * self.v_hist[i] for i in range(self.averaging_count)])
        self.current_av = sum([self.coefficients[i] * self.a_hist[i] for i in range(self.averaging_count)])
        # print(f'V-hist: {self.v_hist} : average = {self.voltage_av}')
        # print(f'A-hist: {self.a_hist} : average = {self.current_av}')

        # Set Charge Level (except for FAULT)
        if self.battery_status == "CHARGING":
            # Adjust charge level w.r.t. charging state
            self.battery_charge = \
                min(100, int(((self.voltage_av - BATTERY_VMIN) / (BATTERY_VMAX + BATTERY_CHRG - BATTERY_VMIN)) * 100))
        elif self.battery_status in ['DISCHARGING', 'FULL']:
            self.battery_charge = \
                min(100, int(((self.voltage_av - BATTERY_VMIN) / (BATTERY_VMAX - BATTERY_DCHG - BATTERY_VMIN)) * 100))
        # If system goes below VMIN, show 0%
        if self.battery_charge < 0:
            self.battery_charge = 0

        # Assert shutdown status if average readings below BATTERY_VMIN
        if self.voltage_av < BATTERY_VMIN:
            # Once set, it cannot be reset without a proper shutdown
            # print("RED REACTOR : Shutdown Required")
            self.shutdown = True

            # Only for PC INA219 model to stop reader thread (ignored by Raspberry Pi)
            if not __debug__:
                if not self.ina.stop:
                    self.ina.finish()
                    self.ina.battery_reader_thread.join()

        # Put INA219 IC device to sleep until next read request
        self.ina.sleep()


# Test code for running stand-alone and shows usage of functions
if __name__ == "__main__":
    """
    Test RRBatMon
    Can use this to create CSV log of battery performance
    
    """

    import time
    import sys

    if len(sys.argv) < 2:
        print("No averaging depth given, will average over 4 readings")
        averaging_interval = 4
    else:
        averaging_interval = int(sys.argv[1])
        print("Averaging over every {} readings".format(averaging_interval))

    # Initialise RedReactor and set measurement interval
    try:
        battery = RRBatMon()
    except RuntimeError as e:
        print("Can't run RR_BatMon:", e)
    else:
        with open("RR_BatMon.log", "w") as log_file:
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
                    # Use 1 second sampling interval
                    time.sleep(1)

                if battery.shutdown:
                    print("Battery SHUTDOWN Detected")
                if battery.battery_status == "FAULT":
                    print("Battery ERROR Detected")

            except KeyboardInterrupt:
                print("UI: User shutdown request detected")
                # Only for PC INA219 model testing
                if not __debug__:
                    print("Stopping PC INA219")
                    if not battery.ina.stop:
                        battery.ina.finish()
                        battery.ina.battery_reader_thread.join()

    print("Exiting RRBatMon Test")
