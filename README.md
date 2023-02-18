# The RedReactor
<b>Hi!
  
  Welcome to the sample code and documentation for the Red Reactor, the ultimate battery power supply for all your Raspberry Pi projects.</b>
  
** Our Kickstarter campaign has now finished, so we are busy with testing and shipping boards! We are live with a pre-order form in case you missed our campaign or would like to order more units, please check our website at https://www.theredreactor.com/ **

But you can still see the story of our campaign journey on our <a href="https://www.kickstarter.com/projects/pascal-h/the-red-reactor-when-power-really-matters">Kickstarter page</a>, which also shows customer comments and our technology updates.

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

## Red Reactor Node-RED Dashboard

Check out our new release of our Red Reactor Node-RED Home Automation Dashboard, which connects to our RR_MQTT client and gives you full visibility and control of your Red Reactor enabled Pi system! Easy to extend to fully automate your own control functions (e.g. alter the battery warning level under high load and temperature), or deploy for multiple devices, you can find out more about the setup on our website at https://www.theredreactor.com/2022/10/25/node-red/ with installation details in our RR_NodeRED folder above (https://github.com/Scally-H/RedReactor/tree/main/RR_NodeRED). We're looking forward to your suggestions for additional features!

## NEW: Mechanical drawing and 3D Models for your custom case designs

We have created a first version of the mechanical drawing and 3D model of the Red Reactor to support you in creating your custom case desigs. We will release these files through this GitHub repository after formal review, until then you can view them on our <a href="https://www.theredreactor.com/news/">news site</a>.

# Production Status
We will update this section with live information about our production status:
- Kickstarter campaign successfully completed on Nov 12th, 2022
- PCB Manufacturing started mid-November with <a href="https://www.pcbway.com/">PCBWAY</a>, where we are part of their <a href="https://www.theredreactor.com/2022/07/06/targetlaunchdate/">Crowdfunding Sponsorship Program</a>
- PCB's received mid-January
- Shipping started mnid-February
- Testing and shipping on-going

## Find out more!

You will find detailed technical information and software configuration guide in the RedReactor User Manual (pdf) - see the above file repository. We've now added a version history (v1.8) to summarise any changes.

For additional help feel free to ask questions, and check out the Youtube channel at https://www.youtube.com/channel/UC3rKXVp0QUgYTzju2NIGytA or contact us on hello@theredreactor.com - we'd love to hear from you.

For more news and regular updates, please visit us at <a href="https://www.theredreactor.com/">www.theredreactor.com</a>

We look forward to seeing you there!
