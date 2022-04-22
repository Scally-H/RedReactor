#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
*** RED REACTOR - Copyright (c) 2022
*** Author: Pascal Herczog

*** This code is designed for the RED REACTOR Raspberry Pi Battery Power Supply
*** Example code provided without warranty
*** Creates a Web Page for remote monitoring of battery status and device usage

# Uses RedReactor_BatteryInfo as battery status monitor
# Uses Flask as web page server
# Access status and config via http://<device_IP_Address:5000/RedReactor
# Includes automatic shutdown at BATTERY_VMIN

*** You may use/modify only for use with the RED REACTOR product
*** Filename: RR_WebMonitor.py
*** PythonVn: 3.8, 32-bit
*** Date: April 2022
"""

# Import battery monitoring class to run as background thread
import RR_WebBat
import RR_Plotgraphs

import time
import threading
import subprocess
from os import path
from datetime import timedelta
from gpiozero import CPUTemperature

from flask import Flask, render_template, request, send_from_directory

app = Flask(__name__)
cpu = CPUTemperature()


# Create Monitor Function
class WebStats:
    """Collects Stats at user defined intervals"""

    def __init__(self):
        # Initialisation
        print("WebStats: Initialising")
        self.interval = 30
        self.history = 100
        self.averaging = 5
        self.log_data = True
        self.average_volts = 0
        self.average_current = 0
        self.temperature = 0
        self.up_time = int(float(open('/proc/uptime').read().split()[0]))
        self.battery_time = 0
        self.ext_power = "Initialising"
        self.op_status = "Initialising"
        self.stop = False

        self.readings = 0
        self.history_volts = list()
        self.history_current = list()
        self.history_temp = list()

        # Open Logfile (but don't write until asked)
        self.log_file = open("RR_WebMonitor.log", 'a')
        if self.log_data:
            self.log_file.write("*" * 50 +
                                "\nAppending New Log Data on {}\n".format(time.asctime()) +
                                "*" * 50 + "\n")

        # Initialise RedReactor
        self.battery = RR_WebBat.RRWebBat()

    def change_settings(self, interval, history, averaging, log_data):
        print("Changing Monitoring Parameters")
        if self.interval != interval and 5 <= interval <= 60:
            self.interval = int(interval)

        if self.history != history and 10 <= history <= 100:
            self.history = int(history)

        if self.averaging != averaging and 1 <= averaging <= 10:
            self.averaging = int(averaging)

        if self.log_data != log_data:
            self.log_data = log_data
            if self.log_data:
                self.log_file.write("*" * 50 +
                                    "\nAppending New Log Data on {}\n".format(time.asctime()) +
                                    "*" * 50 + "\n")
            else:
                self.log_file.write("*" * 50 +
                                    "\n** Suspend Log Data on {} *\n".format(time.asctime()) +
                                    "*" * 50 + "\n")

    def update_bat_status(self):
        # Run as independent thread of web-form activity so can shutdown if necessary
        while not self.stop:
            # Continuously update battery status
            self.battery.get_battery()

            if not self.battery.shutdown:
                # Enable early exit on stop request
                sleep_time = 0
                while sleep_time < 5 and not self.stop:
                    time.sleep(1)
                    sleep_time += 1
                self.up_time += sleep_time
                if self.battery.battery_status == 'DISCHARGING':
                    self.battery_time += sleep_time
                else:
                    self.battery_time = 0
            else:
                print("RR_WebMonitor Shutdown required!")
                self.log_file.write("RR_WebMonitor Shutdown required!\n")
                # Will force a shutdown after clean exit delay
                subprocess.Popen(['sleep 5;sudo shutdown -h now'], shell=True)
                self.log_file.close()
                exit(1)
        # exit due to user stop request
        self.log_file.close()

    def finish(self):
        self.stop = True

    def update_form_data(self):
        # Gather data for web-form update
        if self.readings >= self.history:
            self.history_volts.pop(0)
            self.history_current.pop(0)
            self.history_temp.pop(0)
        else:
            self.readings += 1
        self.history_volts.append(self.battery.voltage)
        self.history_current.append(self.battery.current)
        self.temperature = cpu.temperature
        self.history_temp.append(self.temperature)

        # Take average of available readings within number of readings taken
        self.average_volts = \
            sum(self.history_volts[len(self.history_volts) - min(self.readings, self.averaging):]) \
            / min(self.readings, self.averaging)
        self.average_current = \
            sum(self.history_current[len(self.history_current) - min(self.readings, self.averaging):]) \
            / min(self.readings, self.averaging)

        if self.battery.battery_status == "CHARGING":
            self.ext_power = "Yes, Charging at {}%".format(self.battery.battery_charge)
        elif self.battery.battery_status == "FULL":
            self.ext_power = "Yes, Battery FULL"
        elif self.battery.battery_status == "DISCHARGING":
            self.ext_power = "No, Battery at {}%".format(self.battery.battery_charge)
        else:
            self.ext_power = "BATTERY FAULT!!"

        # Add data from vcgencmd into form
        try:
            cpu_status = subprocess.Popen(['vcgencmd', 'get_throttled'], stdout=subprocess.PIPE)
            cpu_data = cpu_status.communicate()
            cpu_status = int(cpu_data[0].decode().split("=")[1], 16)
            if cpu_status == 0:
                self.op_status = "CPU/GPU OK"
            else:
                self.op_status = cpu_data[0].decode().split("=")[1].strip()
                self.op_status = self.op_status[:3] + " " + self.op_status[3:]
        except (OSError, IndexError, ValueError):
            # Failed to extract info
            self.op_status = "Data Error"

        if self.log_data:
            self.log_file.write(time.strftime("%H:%M:%S", time.localtime()) +
                                ", {:.2f}V, {:7.2f}mA, Ext Power: {}, Uptime: {}, Battery "
                                "Time: {}, Temperature: {:.1f}, CPU: {}\n".format(self.battery.voltage,
                                                                                  self.battery.current,
                                                                                  "Y" if self.ext_power else "N",
                                                                                  self.up_time,
                                                                                  self.battery_time,
                                                                                  self.temperature,
                                                                                  self.op_status)
                                )
            self.log_file.flush()

        # Now plot history date to png file (for requested interval)
        RR_Plotgraphs.rr_plots(self.history_volts[-self.history:],
                               self.history_current[-self.history:],
                               self.history_temp[-self.history:])


@app.route('/favicon.ico')
def favicon():
    # Send favicon
    return send_from_directory(path.join(app.root_path, 'static'),
                               'favicon.ico',
                               mimetype='image/vnd.microsoft.icon')


@app.route('/RedReactor/RR_Status.png')
def rr_status():
    # Send status image
    return send_from_directory(app.root_path, 'RR_Status.png')


@app.route('/RedReactor/', methods=['POST', 'GET'])
def rr_web_monitor():
    print("Updating Status Page")

    if request.method == 'POST':
        try:
            interval = int(request.form['interval'])
            history = int(request.form['history'])
            averaging = int(request.form['averaging'])
            log_data = bool(int(request.form['log_data']))
        except ValueError:
            print("* Form value errors, returning error message")
            return "<h2><b>Invalid Form entry, please 'Go-back' and correct Form inputs</b></h2>"
        else:
            # Will reject out of bounds values
            print("* Updating Parameters :", interval, history, averaging, log_data)
            web_info.change_settings(interval, history, averaging, log_data)

    # Now update form data values and create new graph
    web_info.update_form_data()
    warning = False

    if web_info.battery.battery_status == "FULL":
        colour = full
    elif web_info.battery.battery_status == "CHARGING":
        if web_info.battery.battery_charge < 10:
            colour = charging[0]
        else:
            colour = charging[web_info.battery.battery_charge // 20]
    elif web_info.battery.battery_status == "DISCHARGING":
        if web_info.battery.battery_charge < 10:
            colour = discharging[0]
            warning = True
        else:
            colour = discharging[web_info.battery.battery_charge // 20]
    else:
        # Battery Fault
        colour = fault
        warning = True

    web_stats = {'Interval': web_info.interval,
                 'History': web_info.history,
                 'Averaging': web_info.averaging,
                 'Log_Data': "1" if web_info.log_data else "0",
                 'Last_Volts': "{:.3f}".format(web_info.battery.voltage),
                 'Last_Current': "{:.2f}".format(web_info.battery.current),
                 'Average_Volts': "{:.3f}".format(web_info.average_volts),
                 'Average_Current': "{:.2f}".format(web_info.average_current),
                 'Op_Status': "{}".format(web_info.op_status),
                 'Bat_Charge': web_info.battery.battery_charge,
                 'Bat_Colour': colour,
                 'Ext_Power': web_info.ext_power,
                 'Ext_Warning': warning,
                 'Temperature': web_info.temperature,
                 'Up_Time': "hrs:".join(str(timedelta(seconds=web_info.up_time)).split(":")[:-1]),
                 'Bat_Time': time.strftime("%Hhrs:%Mmins", time.gmtime(web_info.battery_time)),
                 'Time_Now': time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime())
                 }
    return render_template("RR_WebMonitor.html", web_stats=web_stats)


@app.route('/stop/', methods=['POST'])
def rr_stop():
    print("STOP Request received!")
    if request.method == 'POST':
        # Stops update_bat_status thread
        web_info.finish()

        if request.form['stop'] == "Restart":
            # Reboot in 5 seconds, gives time to tidy up
            print("** Rebooting!")
            subprocess.Popen(['sleep 5;sudo shutdown -r now'], shell=True)
            return '<h1 style="color:blue"><b>System is Restarting Now...</b></h1>'
        else:
            # shutdown
            print("*** Shutting Down!")
            subprocess.Popen(['sleep 5;sudo shutdown -h now'], shell=True)
            return '<h1 style="color:red"><b>System is Shutting Down Now...</b></h1>'


# Moved to outside of __main__ to support nginx
# Define battery status colour 0-9 (warning colour), 10-19, 20-39, 40-59, 60-79, 80-99
full = '0,204,0'
fault = '230, 230, 0'
discharging = ('255,0,0', '255,153,0', '204,204,0', '153,204,0', '102,255,51', '51,204,51')
charging = ('204,0,153', '255,0,255', '204,51,255', '153,102,255', '102,102,255', '0,153,153')

# Invoke the WebStats class to manage webpage data
web_info = WebStats()

# Run separate thread to update and monitor battery status for shutdown every 5s
web_info_thread = threading.Thread(target=web_info.update_bat_status, name="RR_BatStatus")
web_info_thread.start()
time.sleep(0.5)

# Start the server framework
if __name__ == "__main__":
    """Runs the Flask Server that handles incoming page requests"""

    print("Starting WebServer for RR_WebMonitor Application")
    app.run(host="0.0.0.0", port=5000, debug=False)
