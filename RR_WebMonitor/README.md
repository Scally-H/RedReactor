# Remote Monitoring Feature for the Red Reactor

The Red Reactor now provides a remote monitoring feature that enables you to see the status information at a glance from your web-browser.

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
  
If not already installed previously, please also install:
```
  sudo pip3 install pi-ina219
  sudo apt install python3-gpiozero
```
  
To run the Flask Webserver with the RR_WebMonitor web application, from within the RR_WebMonitor directory, type:
```
  hostname -I
  python3 RR_WebMonitor.py
```
  
Now head over to your favourite browser, where you'll need the IP address returned by the hostname command (e.g. 192.168.1.20).
Then type the following into the address bar (substiture your actual IP address, but keep the same port number):
  http://192.168.1.20:5000/RedReactor
  
This should show you a page like this:
<img src="RR_WebMon - screenshot.JPG" width="100%"  alt="The Red Reactor Remote Monitor WebApp">
  
Further information can be found on our website, at https://www.theredreactor.com
  
Please write to mailto:hello@theredreactor if you have any feedback or problem with this repository. Your input is appreciated!
