#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
*** RED REACTOR - Copyright (c) 2022
*** Author: Pascal Herczog

*** This code is designed for the RED REACTOR Raspberry Pi Battery Power Supply
*** Example code provided without warranty
*** For use as background task in remote (or no UI) applications
*** Provides battery monitoring services and status updates
*** Requires correct user email SMTP information if email enabled
***
*** Auto-run with sudo crontab -e (files executed from user pi account):

@reboot cd /home/pi/RedReactor/RR_BatMonitor && python3 RR_BatMonitor.py >> RR_BatMon.log 2>&1

# Configurable using constants
# log_data      - log all battery readings to a log file
# send_alerts   - send email alerts on any change [external supply, 100%, 10% and 0%]
# read_interval - read battery voltage, ideally every 5 <= n <= 60 seconds
# BATTERY_VMIN  - shutdown voltage


*** You may use/modify only for use with the RED REACTOR product
*** Filename: RR_BatMonitor.py
*** PythonVn: 3.8, 32-bit
*** Date: September 2022
"""

# Import libraries
import os  # Execute shutdown function
import smtplib  # SMTP library to send the email notification
import socket
import time  # Sleep between reading_interval

from ina219 import INA219, DeviceRangeError  # This controls the battery monitoring IC

# Constants - instead of command line args to keep it simple
# Set to True to write all readings to log file, use as CSV data, else set to False
log_data = True
log_file = "RR_BatLog-" + time.strftime("%m-%d-%H:%M") + ".txt"

# Set to True for email, else set to False to print to console
send_alerts = True

# Suggested interval >5 and <60 seconds
read_interval = 10

# RED REACTOR data
I2C_ADDRESS = 0x40
SHUNT_OHMS = 0.05
MAX_EXPECTED_AMPS = 5.5
BATTERY_ERR = 4.25
BATTERY_VMAX = 4.2

# Charge level warning is based on VMAX - VMIN
# Change BATTERY_VMIN if you want to set an earlier or later shutdown
BATTERY_VMIN = 2.9

# Email setup, example based on gmail
# *** NOTE *** Password is in plain text, GMAIL requires app specific password to protect your account
# *** See Github instructions on how to create app specific password
smtp_username = "name@googlemail.com"  # Replace with your username used to login to your SMTP provider
smtp_password = "email-app-pwd"  # Replace with your password used to login to your SMTP provider
smtp_host = "smtp.gmail.com"  # Replace with the host of the SMTP provider, e.g. mail.isp_name.com
smtp_port = 587  # Check the port that your SMTP provider uses
smtp_sender = "name@googlemail.com"  # Replace with your FROM email address, may be same as smtp_username

smtp_name = socket.gethostname().split(".")[0]  # Sender name - Your board's Hostname
smtp_receivers = [smtp_sender]  # Will send to yourself

# Template message, note triple quotes to force string format
message_template = "From: " + smtp_name + " <" + smtp_sender + """>
To: Me <""" + smtp_sender + """>
Subject: RR Battery Monitor Update\n\n
"""

message_ok = "External power OK\nBattery at "
message_bat = "NO External Power!\nContinuing on Batteries at "
message_low = "The Battery is <= 10%, no external power\nPlease help!"
message_empty = "The Battery is now EMPTY, shutting down immediately.\nGoodbye!"
message_error = "System Error reading battery information.\nPlease check! - "

# Detect state changes; 0=charging, 1=full, 2=discharging, 3=bat low, 4=shutdown, 5=Rd Error, 6=No Bat
status_info = ["Charging", "FULL", "Discharging", "BAT LOW", "SHUTDOWN", "READ ERROR", "NO BATTERY"]
old_status = -1
new_status = 2

external_power = False
charge_level = 0
message_text = ""
shutdown = False


def send_email(smtp_message):
    # Send email, carry on if fails
    try:
        # Note, check your SMTP server login requirements
        # print("Sending Email")
        smtp_obj = smtplib.SMTP(smtp_host, smtp_port)
        smtp_obj.starttls()
        smtp_obj.login(smtp_username, smtp_password)
        smtp_obj.sendmail(smtp_sender, smtp_receivers, message_template + smtp_message)
        return True
    except (smtplib.SMTPException, socket.error) as email_error:
        if log_data:
            write_log(0, 0, 0, "EMAIL ERROR: " + str(email_error))
        if not send_alerts:
            print(email_error)
        return False


def write_log(bat_v, bat_i, bat_charge, bat_state):
    with open(log_file, "a") as logfile:
        logfile.write("{},{:.2f},{:.2f},{},{}\n".format(time.strftime("%H:%M:%S"),
                                                        bat_v, bat_i, bat_charge, bat_state))


# Clear log file with new header if required
if log_data:
    with open(log_file, "w") as log:
        log.write("Red Reactor BatMonitor Log for " + smtp_name + " at " + time.strftime("%Y-%m-%d - %H:%M") + "\n")
        log.write("Time,Volts (V),Current (mA),Charge %,State\n")

# Verify that RED REACTOR is attached
try:
    ina = INA219(SHUNT_OHMS, MAX_EXPECTED_AMPS, busnum=1)
    ina.configure(ina.RANGE_16V)

except OSError as error:
    if send_alerts:
        # If running before network access, wait short while (~100s max) then time out
        print("RED REACTOR STARTUP ERROR - checking internet access to send email")
        for i in range(20):
            try:
                # Choose any (reliable) target domain:port
                socket.create_connection(("www.google.com", 80), timeout=3.1)
                break
            except (OSError, TimeoutError, ConnectionError) as e:
                # Short delay before trying again
                time.sleep(2)
        send_email(message_error + str(error))
    else:
        print(message_error + str(error))
    if log_data:
        write_log(0, 0, 0, "STARTUP ERROR: " + str(error))
    # Error reading battery status, hence you may wish to force a shutdown instead
    # os.system("sudo shutdown now")
    exit(1)

else:
    # Now loop until shutdown condition, only email on state changes
    while not shutdown:

        volts = ina.voltage()
        charge_level = int(max(min(100, (volts - BATTERY_VMIN) / (BATTERY_VMAX - BATTERY_VMIN) * 100), 0))
        try:
            # <0 is charging, <10 is FULL, >10 is discharging
            current = ina.current()

        except DeviceRangeError as e:
            # Current out of device range with specified shunt resistor
            # Assume no ext power so it will still shutdown on low voltage reading
            external_power = False
            new_status = 5
            current = 6000
            message_text = message_error + status_info[new_status]
        else:
            # Identify status change
            if current > 10:
                # External power was removed
                external_power = False
                new_status = 2
                message_text = message_bat
            elif current >= 0:
                # Battery now Full
                external_power = True
                new_status = 1
                message_text = message_ok + "(FULL) "
            else:
                # Still charging
                external_power = True
                new_status = 0
                message_text = message_ok

            message_text += "{}%".format(charge_level)

        if charge_level <= 10 and not external_power:
            message_text = message_low
            new_status = 3

        if charge_level == 0 and not external_power:
            message_text = message_empty
            new_status = 4
            shutdown = True

        if volts > BATTERY_ERR:
            external_power = True
            new_status = 6
            message_text = message_error + status_info[new_status]

        if new_status != old_status:
            old_status = new_status
            if send_alerts:
                # Schedule resend if failed
                if not send_email(message_text):
                    old_status = -1
            else:
                print(message_text)

        if log_data:
            write_log(volts, current, charge_level, status_info[new_status])

        # Now wait till next reading
        if not shutdown:
            time.sleep(read_interval)

    # Exit from while loop due to battery empty
    # Shutdown system
    os.system("sudo shutdown now")
