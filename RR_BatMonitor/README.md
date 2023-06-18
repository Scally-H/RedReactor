<H1>RR Battery Monitor Background App</H1>

This Red Reactor Battery Monitor Background App is an application designed for systems without a display ('Headless'), or are remotely located, or just need to run largely un-attended, and where you need:

- A background application that continuously monitors the battery status
- Can email you updates whenever the battery status changes
- Create a CSV log file of all battery readings for performance analysis
- Warn you by email when the battery is running low
- Automatically execute a safe shutdown at the right time (with a final goodbye email!)
- Easily scheduled to automatically start at boot

The RR_BatMonitor can be easily configured to launch as a background task at boot time, and will immediately start monitoring the system status whilst your system performs all the tasks it is normally set up to do with your own or 3rd party applications.

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
  cd RR_BatMonitor
```

If not already installed previously, please also install:
```
  sudo pip3 install pi-ina219
```
(Please remember to enable the I2C bus under the Advanced Options of raspi-config or via the GUI, as documented in the Red Reactor instruction manual - you will need to reboot the Pi for this to take effect.)

<H2>Before you run the application </h2>

To keep the application as simple as possible to configure and run, you should confirm the options you need by editing the RR_BatMonitor.py file as follows:

> log_data = True # Change this to False if you do not need battery data to be logged, will print to stdout (console) instead<br>
> send_alerts = True # Change this to False if you do not need any email status alerts<br>
> read_interval = 10 # Change the battery read interval, 10 seconds is suggested, but typically >=5 and <60<br>
> BATTERY_VMIN = 2.9 # Change this if you prefer to shutdown at a different level

Note, if you want to run the application interactively it may be useful to set log_data to FALSE to see the information directly on the console shell, e.g. for testing your email settings

If you wish to receive email alerts you will also need to configure the email SMTP settings.

The example below is based on using gmail. For this app to authenticate with Google you will need to set up an app specific password - please follow the instructions at https://support.google.com/accounts/answer/185833 - 'Create & Use App Passwords' to generate a unique password. For 'Select App' choose 'Other', and for 'Select Device' you can use your device hostname to easily remember where it is used. Then paste the password into the smtp_password string field. You may get a gmail to confirm your new settings.

> smtp_username = "name@googlemail.com" # Replace with your username used to login to your SMTP provider<br>
> smtp_password = "email_app_pwd"       # Replace with your password used to login to your SMTP provider<br>
> smtp_host = "smtp.gmail.com"          # Replace with the host of the SMTP provider, e.g. mail.isp_name.com<br>
> smtp_port = 587                       # Check the port that your SMTP provider uses for sending mail<br>
> smtp_sender = "name@googlemail.com"   # Replace with your FROM email address, may be same as smtp_username

Any errors in sending emails will be reported into the log file or the console depending on log_data.

It may be useful to run the application interactively first to check for any system errors, email issues etc. To do so, start from within the RedReactor/RR_BatMonitor folder.

If you have set log_data to False, type:
```
  python3 RR_BatMonitor.py
```
and you will see reports printed to the console as it measures the battery at read_interval intervals.

If you have set log_data to True, type:
```
  python3 RR_BatMonitor.py &
```
This will run the application in the background, allowing you to view the log file contents as it is being written to. To check the log file, use:
```
ls -ltr
```
to find the name of the log file at the bottom of the directory listing, then use this file name to track it:
```
tail -f RR_BatLog-<timestamp>.txt
```
The log file is timestamped when the application is run so that if the system is rebooted it will not overwrite the previously logged data.

The log file is written in CSV format to make it easy to import into Excel should you wish to analyse the voltage and current usage, or review power outage durations etc.

<H2>Configure to run at Boot time</h2>

It is advised to use the log_data = True option since any console output will not be visible when run at boot as a background task.

<H3>Using CRON to run RR_BatMonitor</H3>
There are various ways you can configure the RR_BatMonitor application to run at boot time. For simplicity it is suggested to use CRON, as shown below. This way it will catch an immediate shutdown requirement at the earliest opportunity.

When using CRON, note that depending on other software activities the RR_Batmonitor application may start before internet access is fully established. In this case, the RR_Batmonitor will log an email failure but will continue to try to send status emails at each read_interval until successful, then again only if the battery status changes as described below.

Use the following command to edit the root (so it can run first thing at boot) CRON list:
```
sudo crontab -e
```
=> then select an editor like nano if not used before

Then paste the following line at the end ['2>&1' redirects stderr to stdout, going to RR_Batmon.log]:
```
@reboot cd /home/pi/RedReactor/RR_BatMonitor && python3 RR_BatMonitor.py >> RR_BatMon.log 2>&1
```
=> To exit press CTRL-X and then Y + ENTER to save the file.

After rebooting, you may already have received your first email but you can check that it is running by typing:
```
ps -aux | grep RR
```
which should show you an entry representing the process (and its process id number) of this application. If you wish to stop it manually you can use:
```
sudo kill <process id number>
```

An easy test is to remove external power and check that you receive an email soon after, or view the log file.

If the application is not running you can check for any CRON errors by typing:
```
cat /var/log/syslog | grep RR
```
=> Any application errors are redirected to the RR_BatMon.log file (overwritten on reboot).

<H3>Using systemd service to run RR_BatMonitor</H3>
To run RR_BatMonitor as a systemd service, instead of via CRON, please use the following commands to install the service:

```
sudo cp RR_BatMonitor.service /lib/systemd/system/RR_BatMonitor.service
sudo systemctl enable RR_BatMonitor.service
sudo systemctl start RR_BatMonitor.service
sudo systemctl status RR_BatMonitor.service
```
This will start the service immediately, but also automatically again when booting. The status command will show it running.

The RR_BatMonitor.service file defines that if the service terminates with an error it will be restarted again after <b>RestartSec</b> 5 seconds. However, since RR_Batmonitor will automatically ignore email send errors (and simply try again at the next interval), the service is set to restart only once to avoid flooding your inbox. You can change this by editing <b>StartLimitBurst</b> which sets the number of restarts allowed within <b>StartLimitIntervalSec</b> seconds. If you decide to change these values after installing the service, do remember to copy the service file to /lib/.. again!

<H2>Application Features</H2>

The RR_Batmonitor can log the voltage, current, charge percentage and charge status for every battery reading. It can also log any email send errors.

If emails are enabled, it will only send an update when the status changes, with the following states defined:

> CHARGING        # Implies external power is ON<br>
> FULL            # Implies external power is ON<br>
> DISCHARGING     # Implies external power if OFF<br>
> BAT LOW         # Defined as 10% of available battery voltage range and no external power<br>
> SHUTDOWN        # Occurs at 0% (Change BATTERY_VMIN to set 0% level) and no external power<br>
> READ ERROR      # Unable to read battery voltage/current, or current reading out of range error*<br>
> NO BATTERY      # Implies external power is ON

* In the case of a READ ERROR due to current out of range, the application will assume there is no external power and use the voltage reading to ensure the shutdown condition is checked.

If the SHUTDOWN state is triggered, the application will send a final email and immediately execute an OS shutdown system command. On completion the Red Reactor will automatically turn off its voltage regulator.

<H2>HELP!</H2>

If you have any problems installing this application please send us a message on support@theredreactor.com and we'll be sure to help!

<H2>Where can I get a Red Reactor?</H2>
You can order your Red Reactor from our website at https://www.theredreactor.com/pre-order/ - simply fill in the form and we'll email you an invoice. Pay by Paypal and we'll ship straight away!
