# RedReactor
Hi and welcome to the sample code and documentation for the Red Reactor.

The Red Reactor is designed to fit underneath your Raspberry Pi, leaving the 40-pin header free for all the sensors, displays and other gadgets that you want to use in your projects. With ultra-low stand-by power, and seamless transition even at high currents between the battery and external power, it ensures your data is safe and your design just keeps on working.
A wide range of features enable you to quickly create a robust system, including accurate access to the battery voltage and current, simple ON button integration and RUN/RESET support, battery protection and carefully managed charging circuitry to maximise battery life.

The RedReactor_BatteryInfo.py file shows you how to run a background task to monitor the battery voltage.
It also measures current (and determines if a charger is attached) and sets a shutdown flag when reaching a user specified minimum voltage, that you can use to force a system shutdown

To run the RedReactor_Batteryinfo.py file you will first need to install the INA219 library (python3):

`sudo pip3 install pi-ina219`

(for help with these libraries please visit their respective sites)

The RedReactor_Button.py file to show you how to use the button input, and detect short, medium and long presses.

To run the RedReactor_BatteryInfo.py file you will first need to install the GPIO-Zero library (pyhton3):

`sudo apt install python3-gpiozero`

(for help with these libraries please visit their respective sites)

Full documentation is provided by the Red Reactor Manual.pdf, which includes Raspberry Pi configuration instructions.

For additional help feel free to ask questions, and check out the Youtube channel.

The Red Reactor will be launching soon on Kickstarter, we look forward to seeing you there!
