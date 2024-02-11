<H1>RR_BatWay WAYLAND SystemTray Battery Widget</H1>

:exclamation: You can still run our [pi-battery-widget](https://github.com/Scally-H/pi-battery-widget) 
under the _X11 window manager_ in **Raspberry Pi Boookworm OS**, but it is currently not supported 
in the new **Wayland** window manager (the default for Raspberry Pi 4, but X11 remains available 
via raspi-config).

:heavy_check_mark:This Red Reactor Battery System Tray Application is an application specifically designed for
the Raspberry Pi Wayland Window Manager in Pi Bookwork OS (but it will also run on X11, see below).

![New RedReactor SystemTray widget for Bookworm Wayland](https://github.com/Scally-H/RedReactor/blob/main/RR_BatWay/RR_BatWay_Pi_%20Bookworm_Wayland.png "RedReactor on Raspbbery Pi Bookworm Wayland")

<H2> Special Features</H2>

- Auto-launches onto your Taskbar SystemTray
- Configurable sample and display update rates
- Clear Icons for FULL, DISCHARGING, CHARGING status with pop-up for Voltage and Current
- Status Menu for optional continuous display of voltage, current, CPU temperature and state etc
- Optional pop-up warning on loss of external power
- Pop-up warning when the battery is running low (<30%))
- Pop-up warning when shutdown is imminent (<10%))
- Log file with battery state transitions and debug option for recording of battery samples
- Automatically execute a safe shutdown at preset voltage (set to 2.9v in RR_BatMon)

The RR_BatWay can be easily configured through a .ini file and uses a minimum of system resources. 

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
  cd RR_BatWay
```

If not already installed previously, **then specifically for Raspberry Pi Bookworm** 
the required python INA219 library requires a temporary workaround. Then please use 
(or edit python version accordingly):
```
  sudo mv /usr/lib/python3.11/EXTERNALLY-MANAGED /usr/lib/python3.11/EXTERNALLY-MANAGED.old
  sudo pip3 install pi-ina219
  sudo mv /usr/lib/python3.11/EXTERNALLY-MANAGED.old /usr/lib/python3.11/EXTERNALLY-MANAGED
```
(Please remember to enable the I2C bus under the Advanced Options of raspi-config or via the GUI, 
as documented in the Red Reactor instruction manual - you will need to reboot the Pi for this to take effect.)

For this application you also need to install the PyQt5 python library, as follows:
```
  sudo apt-get install python3-pyqt5
```

<H2>Before you run the application </h2>

You can set a number of application parameters by editing the **RR_BatWay.ini** file as follows (integers only):

| .ini entry | Range | Default | Purpose |
| --- | --- | --- | --- |
| sample_interval | 1 - 20 | 1 | Seconds between battery samples |
| sample_average | 1 - 5 | 5 | Number of samples averaged for battery tooltip |
| report_samples | 1 - 5 | 5 | Number of sample_intervals for tray icon update |
| warn_powerloss | true - false | true | Enables power loss pop-up |

The defaults will sample every second and provide a tray icon update every 5 samples.

You can test the application by running it interactively from a terminal window:

```
  python3 RR_BatWay.py
```
and you will see the icon appear in the System Tray of the status bar.

Once running, you can hover over the battery icon for the tooltip information, or **right click** 
for a status menu and exit menu.

The CPU status is derived from the vcgencmd with its output translated as:

- 0x0      - No voltage / temperature throttling
- 0x0 0001 - under-voltage
- 0x0 0002 - currently throttled
- 0x0 0004 - arm frequency capped
- 0x0 0008 - soft temperature limit reached
- 0x1 0000 - under-voltage has occurred since last reboot
- 0x2 0000 - throttling has occurred since last reboot
- 0x4 0000 - arm frequency cap has occurred since last reboot
- 0x8 0000 - soft temperature limit reached since last reboot

(if multiple conditions exist the numbers are added together, e.g. 0x4000 + 0x8000 = 0xC0000)

<H2>Configure to launch with Desktop</h2>

Simply enable the script for execution and run the installer (updates wayfire.ini):
```
  chmod +x RR_BatWay.sh
  chmod +x install
  ./install
```

This will simply add a line to the Wayland.ini file to run RR_BatWay.py at Desktop launch.
*** **Note that this is only added for the current user** ***

<H2>Additional Application Features</H2>

* Use the Status menu to view every battery sample, useful for tracking power usage
   * Also shows time on battery power, CPU temperature and throttling status 
* Use the debug log features to save battery samples to the log file for off-line processing
   * Set c_log_level to DEBUG to view output interactively
   * Set f_log_level to DEBUG to save debug messages to the RR_BatWay.log file
* Shows battery faults (e.g., no batteries, or battery charging fault)
* Failure to detect the Red Reactor will provide an error pop-up and force user exit

If the SHUTDOWN state is triggered, the application will provide a final pop-up before executing
the OS shutdown system command. On completion the Red Reactor will automatically turn off its 
voltage regulator and output power.

<H2>Wayland Autostart</H2>
:exclamation: Please note that as of 10 Feb 2024, with a fully updated Pi Bookworm OS and 
PyQt5 version 5.15.9, <b>a bug in Wayland/PyQt5</b> means that although RR_BatWay.py auto-starts at boot, 
a start-up delay is required to ensure that the Battery icon is shown in the System Tray.<br>
<br>
There is currently a 5-second delay work-around in <b>RR_BatWay.sh</b> to manage this, but if the 
Battery icon does not show due to other system tasks delaying the creation of the System Tray 
you may need to increase this value. It seems the <b>QSystemTrayIcon.isSystemTrayAvailable()</b> 
never gets set if the application is run before the System Tray is actually available. 
<i>Grateful for any feedback you may have on this!</i>

<H2>Installation for X11 Window Manager</H2>
You might prefer our pi-battery-widget at https://github.com/Scally-H/pi-battery-widget if you're 
only running the X11 Window Manager, <b>BUT RR_BatWay runs on X11 as well as Wayland!</b><br>
<br>

So, if you want an autostart for X11, simply run:
```
  chmod +x RR_BatWay.sh
  chmod +x install_x11
  ./install_x11
``` 
This will copy the system's X11 autostart file to your user account and add RR_BatWay. If you run both 
installers you can easily switch between X11 and Wayland too.

<H2>HELP!</H2>

If you have any problems installing this application please send us a message on 
support@theredreactor.com and we'll be sure to help! :thumbsup:

We'll also happily consider feature requests, though I hope the code is commented enough to
have a go yourself! :smiley:

<H2>Where can I get a Red Reactor?</H2>
You can order your Red Reactor from our website at https://www.theredreactor.com/order - simply fill 
in the form and we'll email you an invoice. Pay by Paypal and we'll ship straight away!
