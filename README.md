# The RedReactor
<b>Hi!
  
  Welcome to the sample code and documentation for the Red Reactor, the ultimate battery power supply for all your Raspberry Pi projects.</b>
  
**We are now live on Kickstarter! So please visit us at https://www.kickstarter.com/projects/pascal-h/the-red-reactor-when-power-really-matters for some great options!**

<img src="RedReactor Pi UPS.jpg" width="50%"  alt="The Red Reactor Raspberry Pi 18650 UPS">

The Red Reactor is designed to fit underneath your Raspberry Pi, leaving the 40-pin header free for all the sensors, displays and other gadgets that you want to use in your projects. With ultra-low stand-by power, and seamless transition even at high currents between the battery and external power, it ensures your data is safe and your design just keeps on working.
A wide range of features enable you to quickly create a robust system, including accurate access to the battery voltage and current, simple ON button integration and RUN/RESET support, battery protection and carefully managed charging circuitry to maximise battery life.

The RedReactor_BatteryInfo.py file shows you how to run a background task to monitor the battery voltage.
It also measures current (and determines if a charger is attached) and sets a shutdown flag when reaching a user specified minimum voltage, that you can use to force a system shutdown

**Installing the required libraries**

To run the RedReactor_Batteryinfo.py file you will first need to install the INA219 library (python3):

```
sudo pip3 install pi-ina219
```
Please remember to enable the I2C bus under the Advanced Options of raspi-config or via the GUI, as documented in the Red Reactor instruction manual (you will need to reboot the Pi for this to take effect).

(You can find more information about this library for your own code at https://github.com/chrisb2/pi_ina219 )

To run the RedReactor_Button.py file you will first need to install the GPIO-Zero library (python3):

```
sudo apt install python3-gpiozero
```

(for help with these libraries please visit their respective sites)

**Installation of example code**

After installing the above libraries, type the following if you don't have these github files yet:
```
  cd
  git clone https://github.com/Scally-H/RedReactor
  cd RedReactor
```

Or if you just want to update the files, type:
```
  cd ~/RedReactor
  git pull
```

**Running the example code**

Use the RedReactor_Button.py file to show you how to use the button input, and detect short, medium and long presses:
```
  python3 RedReactor_Button.py
```

To see the battery voltage and current consumption, type:
```
  python3 RedReactor_BatteryInfo.py
```

Full documentation is provided by the Red Reactor Manual.pdf, which includes Raspberry Pi configuration instructions.

## We're pleased to announce the first release of our LXDE GUI battery widget!
It is available from https://github.com/Scally-H/pi-battery-widget and autostarts itself perfectly into your widget taskbar, showing you charge level, battery status and carefully modelled remaining charge and discharge times!

## New Remote Monitoring using your Web Browser!
Head over to the RR_WebMonitor folder (see file listing above) to use your browser to remotely access all the battery status information, and even request a shutdown or restart of your system. Please see further instructions in the RR_WebMonitor README file.

## Check out our new Battery Monitor with email alerts!
Head over to the RR_BatMonitor folder (see file listing above) for a background battery monitor application that can email you on any battery state changes and manage a safe shutdown - perfect for 'headless' (no GUI) or unattended systems!

## Home Automation with our Red Reactor MQTT Client!
Head over to the RR_MQTT folder (see file listing above) for our first release of our MQTT client to publish full battery status updates to your favourite MQTT Broker and Home Automation system, whilst monitoring the battery voltage to ensure a safe shutdown. Full details are in the readme file.

## Install for Ubuntu 22.04 LTS
We have now tested the configuration and setup requirements for <b>Ubuntu 22.04 LTS</b> (tested on the 64-bit Desktop edition) and documented the changes you need to apply on our website at https://www.theredreactor.com/2022/10/14/ubuntu/ - please follow these instructions first before adding and using these libraries/applications. Do let us know if your setup is behaving differently!

### Find out more!

You will find detailed technical information and software configuration guide in the RedReactor User Manual (pdf) - see the above file repository.

For additional help feel free to ask questions, and check out the Youtube channel at https://www.youtube.com/channel/UC3rKXVp0QUgYTzju2NIGytA or contact us on hello@theredreactor.com - we'd love to hear from you.

The Red Reactor is now LIVE on Kickstarter at https://www.kickstarter.com/projects/pascal-h/the-red-reactor-when-power-really-matters

We look forward to seeing you there!
