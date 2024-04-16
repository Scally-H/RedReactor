#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
*** RED REACTOR - Copyright (c) 2024
*** Author: Pascal Herczog

*** This code is designed for the RED REACTOR Raspberry Pi Battery Power Supply
*** Code provided without warranty
*** Runs battery monitor and reports status via taskbar icon and menu
*** Designed for use with Pi Bookworm WAYLAND window manager
*** Requires configuration file (RR_BatWay.ini) in current directory
*** Creates appended LOG file in RR_BatWay.log
***

*** You may use/modify only for use with the RED REACTOR product
*** Filename: RR_BatWay.py
*** PythonVn: >=3.8
*** Date: February 2024
"""

# Import libraries
# Changes for Ubuntu 22.04
# Replaced PyQt5 with PySide6
# PySide6 has QAction in QtGui library not QtWidgets
from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QMessageBox
from PySide6.QtGui import QIcon, QFont, QAction
from PySide6.QtCore import QTimer

import logging
import subprocess
from os import system

# Manage Battery readings and shutdown control
import RR_BatMon

RR_Version = "1.0"


class TrayIcon(QSystemTrayIcon):
    # TrayIcon class references QSystemTrayIcon class

    def __init__(self, icons, sample_timer=1000, report_count=5, rr_battery=None, parent=None):
        # Inherits from QSystemTrayIcon
        QSystemTrayIcon.__init__(self, parent)

        # Capture configuration
        self.iconset = icons
        self.sample_timer = sample_timer
        self.samples = 0
        self.report_count = report_count
        self.battery = rr_battery

        # Track status and notifications to avoid spamming
        self.track_notifications = {'Powerloss': False,
                                    'Warning': False,
                                    'Shutdown': False,
                                    'Fault': False,
                                    'Error': False,
                                    'BatteryTime': 0,
                                    'LastState': 'N/A'}

        # Creating a menu for the tray
        self.menu = QMenu()

        # Create exit QAction for the menu
        exit_action = QAction("Exit", self)
        # Warn user at exit
        exit_action.triggered.connect(self.check_exit)

        # If Red Reactor OK prepare other menus
        if self.battery is not None:
            # Create status QAction for the menu
            status_action = QAction("Status", self)
            status_action.triggered.connect(self.status)

            # Create status QAction for the menu
            about_action = QAction("About", self)
            about_action.triggered.connect(self.about)

            # Create reset of charge cycle count menu
            reset_action = QAction("Reset", self)
            reset_action.triggered.connect(self.reset)

            # Adding actions to the menu
            self.menu.addAction(status_action)
            self.menu.addAction(reset_action)
            self.menu.addAction(about_action)
            self.menu.addSeparator()
        else:
            # Force user to exit
            logger.critical(f'Limiting user options to exit')

        # Ensure exit is at the bottom of menu
        self.menu.addAction(exit_action)
        # Setting context menu
        self.setContextMenu(self.menu)

        # Hold popup window objects
        self.msg = None
        self.stats = None

        # Set countdown timer for shutdown sequence in seconds
        self.countdown = 10

        self.timer = QTimer()

        # Configure the timer for taskbar report_update
        if self.battery is not None:
            # Set timer to call report_update every N x 1000 milliseconds
            self.timer.timeout.connect(self.report_update)
            self.timer.start(self.sample_timer)
            # Call update now to initialise icon
            self.report_update()
        else:
            # No Red Reactor battery access
            # Set Error icon, no updates, wait for user exit
            self.setIcon(self.iconset['ERROR'])
            self.setToolTip("** RED REACTOR **\n"
                            "**  NOT FOUND  **")

            # Allow _init_ to complete but run exit popup after __main__ app.exec has run
            QTimer.singleShot(1000, self.check_exit)

    def popup_msg(self, message, level, terminate=False):
        # keep msg reference (self) with show for non-modal use
        self.msg = QMessageBox()
        self.msg.setWindowIcon(self.iconset['LOGO'])
        self.msg.setWindowTitle("RED REACTOR")
        self.msg.setText(message)
        self.msg.setIcon(level)
        # msg.setWindowFlags() WindowStaysOnTopHint
        if not terminate:
            self.msg.show()
        else:
            self.msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            self.msg.setDefaultButton(QMessageBox.No)
            # Modal mode blocks further sampling until exit response
            x = self.msg.exec()
            if x == QMessageBox.Yes:
                logger.info(f'User exited application')
                QApplication.quit()

    def check_exit(self):
        if self.battery is not None:
            self.popup_msg("Exiting will stop monitoring for safe shutdown!\nAre you Sure?",
                           QMessageBox.Warning, terminate=True)
        else:
            logger.critical(f'Forcing user to exit')
            self.popup_msg("** NO RED REACTOR, Exiting **\n"
                           "** Please check your setup! **", QMessageBox.Critical, terminate=True)

    def about(self):
        self.popup_msg(f"The Red Reactor\n"
                       f"v{RR_Version} Feb 2024\n"
                       f"https://www.theredreactor.com/\n"
                       f"(c) Pascal Herczog", QMessageBox.Information)

    @staticmethod
    def reset():
        logger.info(f"Charge Cycles at {config['General']['charge_cycles']} reset to 0 in .ini file")
        config['General']['charge_cycles'] = '0'
        with open(inifile, 'w') as cfg_file:
            config.write(cfg_file)

    def switch_off(self):
        # Called from report_update when shutdown detected
        self.countdown -= 1
        if self.countdown != 0:
            # If user closed popup countdown will continue silently
            self.msg.setText(f"Battery EMPTY!\nShutting down in {self.countdown} seconds")
            # call back for countdown
            self.timer.singleShot(1000, self.switch_off)
        else:
            # Shutdown system
            system("sudo shutdown now")
            # for testing
            # exit(0)

    def status_text(self):
        # Use dedicated pop-up so stay up and refresh at sample_interval

        # Requires vcgencmd from OS, returns throttled=0x0 or
        # 0x0 0001 - under-voltage
        # 0x0 0002 - currently throttled
        # 0x0 0004 - arm frequency capped
        # 0x0 0008 - soft temperature limit reached
        # 0x1 0000 - under-voltage has occurred since last reboot
        # 0x2 0000 - throttling has occurred since last reboot
        # 0x4 0000 - arm frequency cap has occurred since last reboot
        # 0x8 0000 - soft temperature limit reached since last reboot

        try:
            cpu_data = subprocess.Popen(['vcgencmd', 'get_throttled'], stdout=subprocess.PIPE)
            cpu_data = cpu_data.communicate()
            cpu_status = cpu_data[0].decode().split("=")[1]
            cpu_data = subprocess.Popen(['vcgencmd', 'measure_temp'], stdout=subprocess.PIPE)
            cpu_data = cpu_data.communicate()
            cpu_temp = cpu_data[0].decode().split("=")[1].rstrip()
        except Exception:
            # bypass if any failure
            cpu_status = "Unknown"
            cpu_temp = "Unknown"

        ext_power = "YES" if battery.current < 10 else "NO"
        bat_stat = "FAULT" if battery.battery_status == "FAULT" else ext_power
        charge_cycles = config.getint('General', 'charge_cycles')
        m, s = divmod(self.track_notifications['BatteryTime'], 60)
        h, m = divmod(m, 60)
        bat_time = f'{h:02d}:{m:02d}:{s:02d}'

        # Uses monospace font. Note, cpu_status includes \n
        status_msg = f"*** Battery Status ***\n" \
                     f"    {battery.voltage:.2f}V,  {battery.current:.2f}mA\n" \
                     f"Charge       : {battery.battery_charge}%\n" \
                     f"Ext Power    : {bat_stat}\n" \
                     f"On Battery   : {bat_time}\n" \
                     f"Charge Cycles: {charge_cycles}\n" \
                     f"CPU State    : {cpu_status}" \
                     f"CPU Temp     : {cpu_temp}"

        return status_msg

    def status(self):
        # Create status popup if not already displayed
        if self.stats is None:
            self.stats = QMessageBox()
            self.stats.setWindowIcon(self.iconset['LOGO'])
            self.stats.setWindowTitle("RED REACTOR")
            self.stats.setFont(QFont('Courier New'))
            self.stats.setText(self.status_text())
            self.stats.setIcon(QMessageBox.Information)
            logger.info('Starting battery status tracker')
            x = self.stats.exec()
            if x == QMessageBox.Ok:
                logger.info('End of battery status tracker')
                # Clear so no further report_updates
                self.stats = None

    def report_update(self):
        """
        Update samples and report status to screen
        """

        # Sample new values
        battery.get_battery()
        logger.debug(f"{battery.battery_status}, "
                     f"{battery.voltage:.2f}V, {battery.current:.2f}mA at {battery.battery_charge}%")

        if battery.shutdown:
            self.setIcon(self.iconset['EMPTY'])
            self.setToolTip("** BATTERY EMPTY **\n"
                            "** SHUTTING DOWN **")
            logger.critical(f'Battery Shutdown required at {battery.voltage:.2f} Volts')

            # Stop sample timer to just wait for switch_off sequence to complete
            self.timer.stop()

            # Then call switch_off sequence to shutdown
            self.popup_msg(f"Battery EMPTY!\nShutting down in {self.countdown} seconds", QMessageBox.Critical)
            self.timer.singleShot(1000, self.switch_off)

        # Check if need to show new data on status popup
        if self.stats is not None:
            # Update status popup (just use debug mode to save data to file)
            self.stats.setText(self.status_text())

        # Report change of state
        if battery.battery_status != self.track_notifications['LastState']:
            logger.info(f'Battery State change to {battery.battery_status} at {battery.battery_charge}%')
            if battery.battery_status == "FULL" and self.track_notifications['LastState'] != 'N/A':
                # Increment charge cycle whenever reaches FULL (except before initialised)
                charges = config.getint('General', 'charge_cycles') + 1
                logger.info(f'Charge Cycle incremented to {charges}')
                config['General']['charge_cycles'] = str(charges)
                with open(inifile, 'w') as cfg_file:
                    config.write(cfg_file)
            if battery.battery_status == "DISCHARGING" and self.track_notifications['LastState'] != 'DISCHARGING':
                # Reset on-battery timer
                self.track_notifications['BatteryTime'] = 0
                if config['General']['warn_powerloss']:
                    self.popup_msg("External power loss\n"
                                   "Check External Power", QMessageBox.Information)

            self.track_notifications['LastState'] = battery.battery_status

        if self.samples % self.report_count != 0:
            # Only capture new samples
            self.samples -= 1
        else:
            # Else update display, reset sample counter
            self.samples = self.report_count - 1

            if battery.battery_status == "FULL":
                self.setIcon(self.iconset['FULL'])
                tooltip = f"Battery FULL\n{battery.voltage:.2f}V, {battery.current:.0f}mA"
            elif battery.battery_status == "DISCHARGING":
                tooltip = f"Discharging at {battery.battery_charge}%\n{battery.voltage:.2f}V, {battery.current:.0f}mA"
                if battery.battery_charge > 85:
                    self.setIcon(self.iconset['DCHG_4'])
                elif battery.battery_charge > 60:
                    self.setIcon(self.iconset['DCHG_3'])
                elif battery.battery_charge > 30:
                    self.setIcon(self.iconset['DCHG_2'])
                elif battery.battery_charge > 10:
                    self.setIcon(self.iconset['DCHG_1'])
                    # Trigger Action Box
                    if not self.track_notifications['Warning']:
                        logger.info(f'Battery Low Notice at {battery.battery_charge}%')
                        self.popup_msg("Battery Charge LOW!\n"
                                       "Check External Power", QMessageBox.Information)
                        self.track_notifications['Warning'] = True
                else:
                    # Charge < 10%
                    self.setIcon(self.iconset['EMPTY'])
                    # Trigger Action Box
                    if not self.track_notifications['Shutdown']:
                        logger.info(f'Battery Shutdown Warning at {battery.battery_charge}%')
                        self.popup_msg(f"<b>Battery at {battery.battery_charge:.0f}%!<br>"
                                       "Shutting down SOON!",
                                       QMessageBox.Warning)
                        self.track_notifications['Shutdown'] = True

            elif battery.battery_status == "CHARGING":
                # Note a battery fault or read error only notified once
                self.track_notifications['Powerloss'] = False
                self.track_notifications['Warning'] = False
                self.track_notifications['Shutdown'] = False
                tooltip = f"Charging at {battery.battery_charge}%\n{battery.voltage:.2f}V, {battery.current:.0f}mA"

                if battery.battery_charge > 85:
                    self.setIcon(self.iconset['CHRG_4'])
                elif battery.battery_charge > 60:
                    self.setIcon(self.iconset['CHRG_3'])
                elif battery.battery_charge > 30:
                    self.setIcon(self.iconset['CHRG_2'])
                else:
                    self.setIcon(self.iconset['CHRG_1'])
            elif battery.battery_status == "FAULT":
                self.setIcon(self.iconset['FAULT'])
                tooltip = "** RED REACTOR **\n" \
                          "* BATTERY FAULT *"
                if not self.track_notifications['Fault']:
                    logger.info(f'Battery Fault detected')
                    self.popup_msg("RED REACTOR BATTERY FAULT\nPlease Check Battery", QMessageBox.Critical)
                    self.track_notifications['Fault'] = True
            else:
                # If read error occurs during use
                self.setIcon(self.iconset['ERROR'])
                tooltip = "** RED REACTOR **\n" \
                          "** READ ERROR! **"
                if not self.track_notifications['Error']:
                    logger.info(f'Battery Read Error')
                    self.popup_msg("RED REACTOR READ ERROR\nPlease Check Setup", QMessageBox.Critical)
                    self.track_notifications['Error'] = True

            # Apply tooltip
            self.setToolTip(tooltip)

        if battery.battery_status == "DISCHARGING":
            self.track_notifications['BatteryTime'] += int(self.sample_timer / 1000)


# Main application
if __name__ == '__main__':

    # Configure startup
    import configparser

    # Create Log Handlers
    # Create logger, enable all msgs
    logger = logging.getLogger("RR_BatWay")
    # Set to stop INA219 logging
    logger.propagate = False
    # Update level from ini file
    logger.setLevel(logging.DEBUG)

    # Create handlers
    c_handler = logging.StreamHandler()
    f_handler = logging.FileHandler('RR_BatWay.log')

    # Create formatters and add it to handlers
    c_format = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
    f_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%d-%b-%y %H:%M:%S')
    c_handler.setFormatter(c_format)
    f_handler.setFormatter(f_format)

    # Add handlers to the logger
    logger.addHandler(c_handler)
    logger.addHandler(f_handler)

    logger.info("** RR_BatWay Startup **")
    logger.info("Loading configuration")

    logger.info(f'Running python with __debug__ = {__debug__}')

    config = configparser.ConfigParser()
    inifile = 'RR_BatWay.ini'
    config.read(inifile)

    # Validate all ini file entries
    logging_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
    try:
        # Check keys exist and values in range
        # if 1999 > config.getint('General', 'battery_capacity') > 7000:
        #     raise ValueError("Capacity value not 2000-6000")
        if 0 > config.getint('General', 'sample_interval') > 20:
            raise ValueError("Measure Interval not 1-20 seconds")
        if 0 > config.getint('General', 'sample_average') > 5:
            raise ValueError("Measure Averaging not 1-5 samples")
        if 0 > config.getint('General', 'report_samples') > 5:
            raise ValueError("Report Interval not 5-20")
        # Status updates are every N measurement_intervals
        report_interval = int(config['General']['sample_interval']) * int(config['General']['report_samples'])
        if report_interval > 100:
            raise ValueError("Report Interval too long at >100 seconds")
        config.getboolean('General', 'warn_powerloss')
        config.getint('General', 'charge_cycles')
        if config.get('General', 'c_log_level') not in logging_levels:
            raise ValueError
        if config.get('General', 'f_log_level') not in logging_levels:
            raise ValueError
        logger.info("Configuration loaded OK")
    except (KeyError, ValueError, configparser.NoSectionError, configparser.NoOptionError) as e:
        logger.error(f'Configuration error {e}, restoring all defaults to ini file')
        # Set defaults, create ini file and report error
        report_interval = 5
        config['General'] = {
            'battery_capacity': "6000",
            'sample_interval': "1",
            'sample_average': "5",
            'report_samples': "5",
            'warn_powerloss': "false",
            'charge_cycles': "0",
            'c_log_level': "INFO",
            'f_log_level': "INFO"}
        with open(inifile, 'w') as configfile:
            config.write(configfile)

    # Update logging levels, limited to listed set
    c_handler.setLevel(logging.getLevelName(config['General']['c_log_level']))
    logger.info(f"Console log level set to {config['General']['c_log_level']}")
    f_handler.setLevel(logging.getLevelName(config['General']['f_log_level']))
    logger.info(f"File log level set to {config['General']['f_log_level']}")

    # Initialise Battery Monitor
    battery = None
    try:
        battery = RR_BatMon.RRBatMon(config.getint('General', 'sample_average'))
        logger.info("** Red Reactor configured")
    except RuntimeError as error:
        # Log error but continue, show fatal error icon
        logger.critical(f"** {error}")

    app = QApplication([])
    # Need this to prevent closing the app on info messagebox OK
    app.setQuitOnLastWindowClosed(False)

    # Pre-load icons
    icon_choice = {'CHRG_1': QIcon('bat_chrg_1.png'),
                   'CHRG_2': QIcon('bat_chrg_2.png'),
                   'CHRG_3': QIcon('bat_chrg_3.png'),
                   'CHRG_4': QIcon('bat_chrg_4.png'),
                   'EMPTY': QIcon('bat_dchg_0.png'),
                   'DCHG_1': QIcon('bat_dchg_1.png'),
                   'DCHG_2': QIcon('bat_dchg_2.png'),
                   'DCHG_3': QIcon('bat_dchg_3.png'),
                   'DCHG_4': QIcon('bat_dchg_4.png'),
                   'FULL': QIcon('bat_full.png'),
                   'ERROR': QIcon('bat_error.png'),
                   'FAULT': QIcon('bat_fault.png'),
                   'LOGO': QIcon('RedReactor.png')}

    trayIcon = TrayIcon(icon_choice,
                        int(config['General']['sample_interval']) * 1000,
                        int(config['General']['report_samples']),
                        battery, app)

    logger.info(f'Checking if SystemTray is available: {str(trayIcon.isSystemTrayAvailable())}')
    # Currently, if trayIcon.isSystemTrayAvailable() is false, it will never go true
    if not trayIcon.isSystemTrayAvailable():
        def wait_for_sytemtray():
            logger.warning(f'Waiting 5s for sysTray to start = {trayIcon.isSystemTrayAvailable()}')
            if not trayIcon.isSystemTrayAvailable():
                QTimer.singleShot(5000, wait_for_sytemtray)
            else:
                # Try to show Battery Icon
                logger.info('SystemTray finally available')
                trayIcon.show()
        wait_for_sytemtray()
    else:
        # Show the tray icon straight away
        trayIcon.show()

    # Run the app
    app.exec()

    # Returns here after user exit
    print("Terminating Application")

    # Only for PC INA219 model testing (ignored for Raspberry Pi)
    if not __debug__:
        if battery:
            print("Stopping PC INA219 model")
            battery.ina.finish()
