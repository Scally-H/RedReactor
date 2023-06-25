# Remote Monitoring Feature for the Red Reactor

The Red Reactor now provides a remote monitoring feature that enables you to see the status information at a glance from your web-browser.

- <b>New Feature: I2C error handling for systemd service use</b>
- <b>Improved battery fault detection</b>
- <b>Includes: CPU/GPU Throttling status incl. handy tooltip on returned value</b>

**Installation**

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
  cd RR_WebMonitor
```

The RR_WebMonitor.py defines the web address as http://your-Pi-ipaddress:5000/RedReactor, but you can change the port number at the end of that file if necessary.

You must first install a number of supporting libraries, as follows:
```
  pip3 install flask
  pip3 install numpy
  pip3 install matplotlib
```
On some setups, numpy may fail to install everything needed, in which case, you'll also need:
```
  sudo apt-get install libatlas-base-dev
```
Also, if you get the following error, ImportError: numpy.core.multiarray failed to import
=> you will need to force numpy to update using:
```
  pip3 install -U numpy
```
  
If not already installed previously, please also install:
```
  sudo pip3 install pi-ina219
  sudo apt install python3-gpiozero
```
(Please remember to enable the I2C bus under the Advanced Options of raspi-config or via the GUI, as documented in the Red Reactor instruction manual - you will need to reboot the Pi for this to take effect.)
  
To run the Flask Webserver with the RR_WebMonitor web application, from within the RR_WebMonitor directory, type:
```
  hostname -I
  python3 RR_WebMonitor.py
```
  
Now head over to your favourite browser, where you'll need the IP address returned by the hostname command (e.g. 192.168.1.20).
Then type the following into the address bar (substiture your actual IP address, but keep the same port number):
  http://192.168.1.20:5000/RedReactor
  
This should show you a page like this:
<img src="RR_WebMon - screenshot.JPG" width="90%"  alt="The Red Reactor Remote Monitor WebApp">

Simply edit the configuration parameters on the webpage and hit 'Submit' to update the server. The battery is checked every 5 seconds (used for averaged reading values) and the server will be forced to shutdown safely when the battery reaches BATTERY_VMIN (in RR_WebBat.py), set to 2.9v by default. The battery status colour changes for these battery %'s: 0-9, 10-19, 20-39, 40-59, 60-79, 80-99, FULL (charge complete)

<H2>Configure to run at Boot time</h2>

You can use systemd to automate running RR_WebMonitor as a service. RR_WebMonitor has been updated to still enable a remote reboot or shutdown in case of I2C access errors. In case of other system errors, systemd will attempt to restart the RR_WebMonitor service. 
To install the service, please use the following commands:

```
sudo cp RR_WebMonitor.service /lib/systemd/system/RR_WebMonitor.service
sudo systemctl enable RR_WebMonitor.service
sudo systemctl start RR_WebMonitor.service
sudo systemctl status RR_WebMonitor.service
```
This will start the service immediately, but also automatically again when booting. The status command will show it running.

You may need to edit the RR_WebMonitor.service file depending on your setup (e.g. if you are not logged in as user 'pi'). It defines that if the service terminates with an error it will be restarted again after <b>RestartSec</b> 5 seconds.  You can change the thresholds by editing <b>StartLimitBurst</b> which sets the number of restarts allowed within <b>StartLimitIntervalSec</b> seconds. If you decide to change these values after installing the service, do remember to copy the service file to /lib/.. again! (use 'restart' with the systemctl command)

Note that the log file only contains the data sent to an active browser session.

<h2>Where can I get a Red Reactor?</h2>
You can order your Red Reactor from our website at https://www.theredreactor.com/pre-order/ - simply fill in the form and we'll email you an invoice. Pay by Paypal and we'll ship straight away! 

Further information can be found on our website, at https://www.theredreactor.com
  
Please write to hello@theredreactor.com if you have any feedback or problem with this repository. Your input is appreciated!
