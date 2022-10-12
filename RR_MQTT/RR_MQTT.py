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
import logging
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
# Battery voltage may drop slightly after charging complete
BATTERY_VMAX = 4.2 - 0.02

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
        logger.info("Connected to MQTT broker")
        client_connected = True
        mqtt_client.will_set(
            f"{config['hostname']}/{RR_SERVICE}/{RR_SERVICE_STATUS}",
            payload=config['offline'],
            qos=1,
            retain=True,
        )
        if rr_ina:
            mqtt_client.publish(
                f"{config['hostname']}/{RR_SERVICE}/{RR_SERVICE_STATUS}",
                payload=config['online'],
                qos=1,
                retain=True,
            )
        else:
            mqtt_client.publish(
                f"{config['hostname']}/{RR_SERVICE}/{RR_SERVICE_STATUS}",
                payload="RR_Startup_Error",
                qos=1,
                retain=True,
            )

        # For testing, subscribe to all topics
        if logging.DEBUG in [c_handler.level, f_handler.level]:
            logger.debug("Subscribing to topic " + f"{config['hostname']}/{RR_SERVICE}/{RR_SERVICE_STATUS}")
            mqtt_client.subscribe(f"{config['hostname']}/{RR_SERVICE}/{RR_SERVICE_STATUS}")
            logger.debug("Subscribing to topic " + f"{config['hostname']}/{RR_SERVICE}/{RR_SERVICE_DATA}")
            mqtt_client.subscribe(f"{config['hostname']}/{RR_SERVICE}/{RR_SERVICE_DATA}")

        # Subscribe to the command return topic
        logger.info("Subscribing to topic " + f"{config['hostname']}/{RR_SERVICE}/{RR_SERVICE_CMDS}")
        mqtt_client.subscribe(f"{config['hostname']}/{RR_SERVICE}/{RR_SERVICE_CMDS}")
    else:
        logger.error(f"MQTT broker connection refused, error code = {rc}")


def mqtt_on_disconnect(mqtt_client, userdata, rc):
    """Handle temporary network connection issues"""
    global client_connected

    logger.warning(f"Disconnected from MQTT broker: {rc}")
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

    logger.debug(f"message received {str(message.payload.decode('utf-8'))}")
    logger.debug(f"message topic={message.topic}")
    logger.debug(f"message qos={message.qos}")
    logger.debug(f"message retain flag={message.retain}")

    # Commands expected as JSON format string
    try:
        message_data = loads(str(message.payload.decode("utf-8")))
    except JSONDecodeError:
        logger.warning(f"Non-JSON msg received: {str(message.payload.decode('utf-8'))}")
        return

    if "Shutdown" in message_data.keys():
        logger.info("Shutdown command received!")
        mqtt_on_exit(0, 0, 1)

    if "Reboot" in message_data.keys():
        logger.info("Reboot command received!")
        mqtt_on_exit(0, 0, 2)

    if "Interval" in message_data.keys():
        try:
            config['publish_period'] = int(message_data['Interval'])
            logger.info(f"Changed reporting interval to {config['publish_period']}s")
        except ValueError:
            logger.error("Error changing publishing interval")

    if "WARN" in message_data.keys():
        try:
            BATTERY_WARN = float(message_data['WARN'])
            logger.info(f"Changed Warning Threshold to {BATTERY_WARN}V")
        except ValueError:
            logger.error("Error changing Warning Threshold")

    if "VMIN" in message_data.keys():
        try:
            BATTERY_VMIN = float(message_data['VMIN'])
            logger.info(f"Changed Shutdown Threshold to {BATTERY_VMIN}V")
        except ValueError:
            logger.error("Error changing Shutdown Threshold")


def mqtt_on_exit(signum, frame, exit_option=0):
    """
    Update MQTT services' status to `offline`
    Called when local program exit is received.
    """
    global stop_thread

    logger.info("Exiting ...")
    stop_thread = True

    logger.info("Sending offline message")
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
    volts = BATTERY_ERR
    current = 0
    external_power = True
    last_publish = time.perf_counter()

    while not shutdown and not stop():
        if ina:
            volts = ina.voltage()
        charge_level = int(max(min(100, (volts - BATTERY_VMIN) / (BATTERY_VMAX - BATTERY_VMIN) * 100), 0))

        if ina:
            try:
                # <0 is charging, <10 is FULL, >10 is discharging
                current = ina.current()
            except DeviceRangeError:
                # Current out of device range with specified shunt resistor
                # Assume no ext power so it will still shutdown on low voltage reading
                logger.error("Red Reactor Battery Current Range Error")
                external_power = False
                current = 6000
                last_publish = 0
                mqtt_client.publish(
                    f"{config['hostname']}/{RR_SERVICE}/{RR_SERVICE_STATUS}",
                    payload="RR_Range_Error",
                    qos=1,
                    retain=True,
                )

            else:
                # Identify status change
                if current > 10:
                    # No External Power
                    if external_power:
                        # Power removed, publish immediately
                        last_publish -= config['publish_period']
                    external_power = False
                elif current >= 0:
                    # Battery now Full
                    external_power = True
                else:
                    # Charging
                    if not external_power:
                        # Power restored, publish immediately
                        last_publish -= config['publish_period']
                    external_power = True

        if charge_level <= BATTERY_WARN and not external_power:
            # Force immediate publish update at warning level
            last_publish -= config['publish_period']

        if charge_level == 0 and not external_power:
            shutdown = True

        if volts > BATTERY_ERR:
            external_power = True
            # Force immediate publish update on battery error
            last_publish -= config['publish_period']

        # Shutdown system
        if shutdown:
            # Go Offline and shutdown due to battery empty
            logger.info("Forcing system shutdown, going offline at {:.2f}volts".format(volts))
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
            logger.debug("Battery Data: {:.2f}v, {:.2f}mA, {}%, ExtPwr:{}".format(volts, current,
                                                                                  charge_level, external_power))
            if time.perf_counter() - last_publish >= config['publish_period']:
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
                    logger.error("Failed to read CPU info")
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
                    logger.info("Publishing new data")
                    mqtt_client.publish(f"{config['hostname']}/{RR_SERVICE}/{RR_SERVICE_DATA}",
                                        dumps(rr_battery_status))

            # Wait for next status check, typically 5s
            time.sleep(READ_INTERVAL)
    logger.debug("Exiting monitoring loop")


# Entry Point for MAIN program execution
if __name__ == "__main__":
    """Red Reactor MQTT Client startup"""

    # Create logger, enable all msgs
    logger = logging.getLogger("RR_MQTT")
    # Set to stop INA219 logging
    logger.propagate = False
    logger.setLevel(logging.DEBUG)

    # Create handlers
    c_handler = logging.StreamHandler()
    f_handler = logging.FileHandler('RR_MQTT.log')

    # Create formatters and add it to handlers
    c_format = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
    f_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%d-%b-%y %H:%M:%S')
    c_handler.setFormatter(c_format)
    f_handler.setFormatter(f_format)

    # Add handlers to the logger
    logger.addHandler(c_handler)
    logger.addHandler(f_handler)

    logger.info("** RR_MQTT Startup **")
    logger.info("Loading configuration")
    config = load_config(args.config_file)

    # Update logging levels, limited to listed set
    logging_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
    if 'c_log_level' in config.keys():
        if config['c_log_level'] in logging_levels:
            c_handler.setLevel(config['c_log_level'])
            logger.info(f"Console log level set to {config['c_log_level']}")
    if 'f_log_level' in config.keys():
        if config['f_log_level'] in logging_levels:
            f_handler.setLevel(config['f_log_level'])
            logger.info(f"File log level set to {config['f_log_level']}")

    # Verify that the RED REACTOR is attached
    rr_ina = None
    try:
        rr_ina = INA219(SHUNT_OHMS, MAX_EXPECTED_AMPS, busnum=1, log_level=logging.ERROR)
        rr_ina.configure(rr_ina.RANGE_16V)
    except (OSError, ModuleNotFoundError) as error:
        # Log error but continue client (on_connect will send error status)
        logger.error(f"** Unable to connect to the Red Reactor {error}")

    logger.info("RR MQTT Client setup")
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
        # Log error but client loop will continue to try to connect
        logger.error(f"** Unable to connect to the MQTT Broker {error}")

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
