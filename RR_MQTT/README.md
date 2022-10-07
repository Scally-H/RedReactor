<H1>Red Reactor MQTT Client for Home Automation</H1>

This Red Reactor MQTT Client is designed to run as a background application to 
monitor the battery status and publish its data to an MQTT Broker for 
integration with Home Automation systems, such as HomeAssistant and OpenHAB.

<b> This is a first draft release of the RR_MQTT client, tested with the
Mosquito MQTT Broker and OpenHAB, but requires further integration work on 
the Home Automation server side</b>

The RR_MQTT client functions include:

- A background application that continuously monitors the battery status for safe shutdown
- The config.yaml file can be used to set / override device specific configurations
- Connects to an MQTT Broker for Service Status, Data and Command Topics
- Published data includes:
  - Voltage, Current, Battery Charge, External Power status, CPU Temp, CPU Status
- The Command channel enables control and parameter modification for:
  - Immediate shutdown, Immediate Reboot, Battery Warning level, Target Shutdown voltage
- Easily scheduled to automatically start at boot

The RR_MQTT Client can be easily configured to launch as a background task at boot time, and will immediately start monitoring the system status whilst your system performs all the tasks it is normally set up to do with your own or 3rd party applications.

<h2>Installation</h2>

To update a previously downloaded RedReactor:

Open a terminal and type

```
  cd
  cd RedReactor
  git pull
```
or to install from scratch, open a terminal and type:
```
  cd
  git clone https://github.com/Scally-H/RedReactor
  cd RedReactor
```
Once downloaded/updated, type:
```
  cd RR_MQTT
```

If not already installed previously, please also install:
```
  sudo pip3 install pi-ina219
```

This application also needs the python MQTT library, so please install:
```
  pip3 install paho-mqtt
```


Please remember to enable the I2C bus under the Advanced Options of raspi-config or via the GUI, as documented in the Red Reactor instruction manual - you will need to reboot the Pi for this to take effect.


<H2>Before you run the application </h2>

The <b>config.yaml</b> file can be used to set parameters specific to your device and network:

1. Edit the broker IP address (e.g. 192.168.1.2, or 127.0.0.1, or localhost etc.)
2. The default is port 1883, for unsecured access, edit as appropriate
3. Set the MQTT Broker access username / password (default: not required)
4. Adjust the publish_period if necessary (default: 30 seconds)
5. Override the hostname if necessary (default: actual hostname)
6. Override the online/offline text strings if necessary (default: ON, OFF)

It may be useful to run the application interactively first to check for any 
system errors, connection errors etc. To do so, start from within the
RedReactor/RR_MQTT folder.

Type:
```
  python3 RR_MQTT.py
```
and you will see reports printed to the console as it initialises and connects to the MQTT Broker, with any errors shown in the console.

<b>This draft release includes a number of print statements to give more details
about its actions for testing interactively with your MQTT Broker. It also subscribes
to its own Service and Data topics to show its published data sets. The return Command 
channel has not yet been fully tested.</b>

Pressing CTRL-C will gracefully send the OFF (offline) status and exit.

<H2>Configure to run at Boot time</h2>

A systemd service file will be uploaded soon

<H2>Application Features</H2>

On startup the RR_MQTT Client will verify access to the Red Reactor and 
set up a connection to the specified MQTT Broker. On successful connection it
will set the LWT Service topic message to OFF (offline), and publish it's ON status.

If there is a battery status read error, the "RR_READ_Error" status is sent
on the Service topic.

<b>Note that even when if the broker connection is lost, the RR_MQTT application
will continue to check the battery status to ensure a safe shutdown is executed
when necessary. When the connection is re-established, publication of data will
resume.</b>

This enables the publishing of status information on the Data topic, sent as a
json structure string. Data is normally published at the specified publish_period
intervals, but any state change (e.g. external power removed, battery warning etc.)
will force an immediate publish update.

The JSON string format is:
```
{"RR_volts": 4.2, "RR_current": 1, "RR_charge": 100, "RR_extpwr": true, "RR_CPUTEMP": 41.7, "RR_CPUSTAT": 0, "RR_WARN": 10, "RR_VMIN": 2.9}
```

The battery is monitored at a shorter interval (5s) to ensure state changes are
captured immediately.

- RR_volts - Battery voltage (float)
- RR_current - Battery current, in mA, negative means charging (integer)
- RR_charge - Charge level as a percentage (integer)
- RR_extpower - true/false
- RR_CPUTEMP - read via 'vcgencmd measure_temp' (float)
- RR_CPUSTAT - read via 'vcgencmd get_throttled' (integer from 16bit format)
- RR_WARN - Warning Percentage level
- RR_VMIN - Shutdown voltage level

Please see VCGENCMD for information on the values in RR_CPUSTAT, reflecting
CPU throttling conditions.

The RR_WARN value is set to 10 (%) by default, but you may wish to modify this
at run-time if the operational requirements change.

The RR_VMIN is set to 2.9 (v) by default, but you may wish to modify this
at run-time if the operational requirements change.

The RR_MQTT Client is subscribed to the Command topic to receive incoming
commands as a json string format {'command': value} pair.

If the SHUTDOWN or REBOOT state is triggered, the application will set the 
Service topic to OFF (offline) first, then execute the OS shutdown/reboot 
system command. On shutdown completion the Red Reactor will automatically 
turn off its voltage regulator.

<H2>HELP!</H2>

If you have any problems installing this application please send us a message on support@theredreactor.com and we'll be sure to help!

<H2>Where can I get a Red Reactor?</H2>
We are now live on Kickstarter!
So please visit us at https://www.kickstarter.com/projects/pascal-h/the-red-reactor-when-power-really-matters for some great options!
 
