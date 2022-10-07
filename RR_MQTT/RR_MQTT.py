#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
*** RED REACTOR - Copyright (c) 2022
*** Author: Pascal Herczog

*** This code is designed for the RED REACTOR Raspberry Pi Battery Power Supply
*** Example code provided without warranty
*** For use as background task for MQTT based remote monitoring and control
*** Publishes battery monitoring topics and subscribes to a command channel
*** Requires an MQTT broker (e.g. mosquito)
*** Requires configuration file (config.yaml)
***

*** You may use/modify only for use with the RED REACTOR product
*** Filename: RR_MQTT.py
*** PythonVn: 3.8, 32-bit
*** Date: October 2022
"""

# Import libraries
import paho.mqtt.client as mqtt

import socket
import argparse
import yaml
import signal
import subprocess
import threading
import os
import time
from json import dumps, loads, JSONDecodeError

# This controls the battery monitoring IC
from ina219 import INA219, DeviceRangeError

parser = argparse.ArgumentParser(description="Red Reactor MQTT client")
parser.add_argument(
    "-c",
    "--config",
    default="config.yaml",
    help="Configuration yaml file, defaults to `config.yaml`",
    dest="config_file",
)
args = parser.parse_args()

# Make sure that HOST_NAME is unique if you have multiple RedReactor based devices!
HOST_NAME = socket.gethostname()
RR_SERVICE = "RedReactor"
RR_SERVICE_STATUS = "Service"
RR_SERVICE_DATA = "Data"
RR_SERVICE_CMDS = "Command"

# RED REACTOR data
I2C_ADDRESS = 0x40
SHUNT_OHMS = 0.05
MAX_EXPECTED_AMPS = 5.5
BATTERY_ERR = 4.25
BATTERY_VMAX = 4.2

# Define BATTERY_WARN % charge level at which to send immediate MQTT update
BATTERY_WARN = 10
# Change BATTERY_VMIN if you want to set an earlier or later shutdown
BATTERY_VMIN = 2.9

# Important to read battery regularly to check status
READ_INTERVAL = 5


def load_config(config_file):
    """Load the configuration from config yaml file to override the defaults."""
    with open(config_file, "r") as cfg_file:
        config_override = yaml.safe_load(cfg_file)

    default_config = {
        "mqtt": {
            "broker": "127.0.0.1",
            "port": 1883,
            "username": None,
            "password": None,
        },

        "publish_period": 30,
        "hostname": HOST_NAME,
        "offline": "OFF",
        "online": "ON"
    }

    return {**default_config, **config_override}


def mqtt_on_connect(mqtt_client, userdata, flags, rc):
    """Set Last Will message, subscribe to command topic and update service status to broker."""
    global client_connected

    if rc == 0:
        print("Connected to MQTT broker")
        client_connected = True
        mqtt_client.will_set(
            f"{config['hostname']}/{RR_SERVICE}/{RR_SERVICE_STATUS}",
            payload=config['offline'],
            qos=1,
            retain=True,
        )
        mqtt_client.publish(
            f"{config['hostname']}/{RR_SERVICE}/{RR_SERVICE_STATUS}",
            payload=config['online'],
            qos=1,
            retain=True,
        )

        # For testing, subscribe to all topics
        print("Subscribing to topic " + f"{config['hostname']}/{RR_SERVICE}/{RR_SERVICE_STATUS}")
        mqtt_client.subscribe(f"{config['hostname']}/{RR_SERVICE}/{RR_SERVICE_STATUS}")
        print("Subscribing to topic " + f"{config['hostname']}/{RR_SERVICE}/{RR_SERVICE_DATA}")
        mqtt_client.subscribe(f"{config['hostname']}/{RR_SERVICE}/{RR_SERVICE_DATA}")

        # Subscribe to the command return topic
        print("Subscribing to topic " + f"{config['hostname']}/{RR_SERVICE}/{RR_SERVICE_CMDS}")
        mqtt_client.subscribe(f"{config['hostname']}/{RR_SERVICE}/{RR_SERVICE_CMDS}")
    else:
        print("MQTT broker connection refused, error code = ", rc)


def mqtt_on_disconnect(mqtt_client, userdata, rc):
    """Handle temporary network connection issues"""
    global client_connected

    print("Disconnected from MQTT broker: " + str(rc))
    client_connected = False


def on_message(clientid, userdata, message):
    """ Handle incoming commands in json structure
    'Shutdown': 1
    'Reboot': 1
    'Interval': 25
    'WARN': 10
    'VMIN': 3.0
    """
    global config, BATTERY_WARN, BATTERY_VMIN

    print("message received ", str(message.payload.decode("utf-8")))
    print("message topic=", message.topic)
    print("message qos=", message.qos)
    print("message retain flag=", message.retain)

    # Commands expected as JSON format string
    try:
        message_data = loads(str(message.payload.decode("utf-8")))
    except JSONDecodeError:
        print("message received ", str(message.payload.decode("utf-8")))
        return

    if "Shutdown" in message_data.keys():
        print("Shutdown command received!")
        mqtt_on_exit(0, 0, 1)

    if "Reboot" in message_data.keys():
        print("Reboot command received!")
        mqtt_on_exit(0, 0, 2)

    if "Interval" in message_data.keys():
        try:
            config['publish_period'] = int(message_data['Interval'])
            print(f"Changed reporting interval to {config['publish_period']}s")
        except ValueError:
            print("Error changing publishing interval")

    if "WARN" in message_data.keys():
        try:
            BATTERY_WARN = float(message_data['WARN'])
            print(f"Changed Warning Threshold to {BATTERY_WARN}V")
        except ValueError:
            print("Error changing Warning Threshold")

    if "VMIN" in message_data.keys():
        try:
            BATTERY_VMIN = float(message_data['VMIN'])
            print(f"Changed Shutdown Threshold to {BATTERY_VMIN}V")
        except ValueError:
            print("Error changing Shutdown Threshold")


def mqtt_on_exit(signum, frame, exit_option=0):
    """
    Update MQTT services' status to `offline`
    Called when local program exit is received.
    """
    global stop_thread

    print("Exiting ...")
    stop_thread = True

    print("Sending offline message")
    client.publish(
        f"{config['hostname']}/{RR_SERVICE}/{RR_SERVICE_STATUS}",
        payload=config["offline"],
        qos=1,
        retain=True,
    )
    # Short delay ensures msg sent
    time.sleep(5)
    # Check if need to apply client.disconnect

    battery_thread.join()
    if exit_option == 0:
        exit(0)
    elif exit_option == 1:
        # execute shutdown
        os.system("sudo shutdown now")
        # exit(3)
    else:
        # execute reboot
        os.system("sudo reboot now")
        # exit(4)


def publish_battery_status(ina, mqtt_client, stop):
    """Manages shutdown trigger and publish MQTT messages every config[publish_period]
    Run as separate timer thread to monitor battery state
    On_exit will assert stop, terminating thread loop
    """

    shutdown = False
    last_publish = time.perf_counter()

    while not shutdown and not stop():
        volts = ina.voltage()
        charge_level = int(max(min(100, (volts - BATTERY_VMIN) / (BATTERY_VMAX - BATTERY_VMIN) * 100), 0))

        try:
            # <0 is charging, <10 is FULL, >10 is discharging
            current = ina.current()
        except DeviceRangeError:
            # Current out of device range with specified shunt resistor
            # Assume no ext power so it will still shutdown on low voltage reading
            external_power = False
            current = 6000
            mqtt_client.publish(
                f"{config['hostname']}/{RR_SERVICE}/{RR_SERVICE_STATUS}",
                payload="RR_READ_Error",
                qos=1,
                retain=True,
            )

        else:
            # Identify status change
            if current > 10:
                # External power was removed
                external_power = False
                # Force immediate publish update
                last_publish = 0
            elif current >= 0:
                # Battery now Full
                external_power = True
                # Force immediate publish update
                last_publish = 0
            else:
                # Still charging
                external_power = True

            if charge_level <= BATTERY_WARN and not external_power:
                # Force immediate publish update at warning level
                last_publish = 0

            if charge_level == 0 and not external_power:
                shutdown = True

        if volts > BATTERY_ERR:
            external_power = True
            # Force immediate publish update
            last_publish = 0

        # Shutdown system
        if shutdown:
            # Go Offline and shutdown due to battery empty
            print("Forcing system shutdown, going offline at {:.2f}volts".format(volts))
            mqtt_client.publish(f"{config['hostname']}/{RR_SERVICE}/{RR_SERVICE_STATUS}",
                                payload=config["offline"],
                                qos=1,
                                retain=True,
                                )
            time.sleep(5)
            # Shutdown system
            os.system("sudo shutdown now")
            # exit(0)
        else:
            # Publish status at required intervals and sleep till next battery check
            # State changes are published immediately
            print("Battery Data: {},{:.2f},{:.2f},{},{}\n".format(time.strftime("%H:%M:%S"),
                                                                  volts, current, charge_level, external_power))
            if time.perf_counter() - last_publish >= config['publish_period']:
                print("Publishing new data")
                last_publish = time.perf_counter()
                # Add data from vcgencmd into status report
                try:
                    cpu_data = subprocess.Popen(['vcgencmd', 'get_throttled'], stdout=subprocess.PIPE)
                    cpu_data = cpu_data.communicate()
                    cpu_status = int(cpu_data[0].decode().split("=")[1], 16)
                    cpu_data = subprocess.Popen(['vcgencmd', 'measure_temp'], stdout=subprocess.PIPE)
                    cpu_data = cpu_data.communicate()
                    cpu_temp = float(cpu_data[0].decode().split("=")[1].replace("'C", ""))
                except (OSError, IndexError, ValueError):
                    # Failed to extract info
                    cpu_status = 65535
                    cpu_temp = 0

                rr_battery_status = dict(RR_volts=float("{:.2f}".format(volts)),
                                         RR_current=int(current),
                                         RR_charge=charge_level,
                                         RR_extpwr=external_power,
                                         RR_CPUTEMP=cpu_temp,
                                         RR_CPUSTAT=cpu_status,
                                         RR_WARN=BATTERY_WARN,
                                         RR_VMIN=BATTERY_VMIN
                                         )
                if client_connected:
                    mqtt_client.publish(f"{config['hostname']}/{RR_SERVICE}/{RR_SERVICE_DATA}",
                                        dumps(rr_battery_status))

            # Wait for next status check, typically 5s
            time.sleep(READ_INTERVAL)
    print("Exiting monitoring loop")


print("Red Reactor MQTT Loading configuration")
config = load_config(args.config_file)

# Entry Point for MAIN program execution
if __name__ == "__main__":
    """Red Reactor MQTT Client startup"""

    print("Red Reactor MQTT Client setup")
    client = mqtt.Client(client_id=HOST_NAME,
                         clean_session=True, userdata=None, protocol=mqtt.MQTTv311, transport="tcp")
    client.on_connect = mqtt_on_connect
    client.on_disconnect = mqtt_on_disconnect
    client.on_message = on_message
    client_connected = False
    client.username_pw_set(config['mqtt']['username'], config['mqtt']['password'])

    try:
        # Keep Alive default to 60s, decide if you need it shorter
        # An on_connect callback will set client_connected
        client.connect(config['mqtt']['broker'], config['mqtt']['port'], 60)
    except (ConnectionRefusedError, socket.timeout) as error:
        print("** Unable to connect to the MQTT Broker,", error)
        exit(1)

    # Verify that the RED REACTOR is attached
    rr_ina = None
    try:
        rr_ina = INA219(SHUNT_OHMS, MAX_EXPECTED_AMPS, busnum=1)
        rr_ina.configure(rr_ina.RANGE_16V)
    except (OSError, ModuleNotFoundError) as error:
        print("** Unable to connect to the Red Reactor,", error)
        # Limited wait until connected to broker
        client.loop_start()
        for i in range(10):
            if client_connected:
                print("Sending error message")
                client.publish(
                    f"{config['hostname']}/{RR_SERVICE}/{RR_SERVICE_STATUS}",
                    payload="RR_Startup_Error",
                    qos=1,
                    retain=True,
                )
                break
            time.sleep(1)
        # Ensure msg is sent
        time.sleep(5)
        exit(2)

    # Run battery monitor in separate thread, which also publishes MQTT status updates
    stop_thread = False
    battery_thread = threading.Thread(target=publish_battery_status,
                                      name="RedReactor",
                                      args=(rr_ina, client, lambda: stop_thread))
    battery_thread.start()

    # Publish exit if locally terminated
    signal.signal(signal.SIGINT, mqtt_on_exit)
    signal.signal(signal.SIGTERM, mqtt_on_exit)

    # Run forever until battery shutdown or user exit
    client.loop_forever()
