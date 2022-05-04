# The RedReactor
<b>Hi!
  
  Welcome to the sample code and documentation for the Red Reactor, the ultimate battery power supply for all your Raspberry Pi projects.</b>

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

(for help with these libraries please visit their respective sites)

To run the RedReactor_BatteryInfo.py file you will first need to install the GPIO-Zero library (pyhton3):

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

### Find out more!
For additional help feel free to ask questions, and check out the Youtube channel at https://www.youtube.com/channel/UC3rKXVp0QUgYTzju2NIGytA or contact us on hello@theredreactor.com - we'd love to hear from you.

The Red Reactor will be launching very soon on Kickstarter, to sign up for launch news please register at https://www.theredreactor.com

We look forward to seeing you there!
