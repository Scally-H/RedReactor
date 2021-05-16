#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
*** RED REACTOR - Copyright (c) 2021
*** Author: Pascal Herczog

*** This code is designed for the RED REACTOR Raspberry Pi Battery Power Supply
*** Example code provided without warranty
*** Demonstrates how to monitor the ON button so you can use it not just to
*** turn ON your device, but use the same button to detect short, medium and long
*** press actions. You may additionally use the RUN/RESET feature to force a
*** hard reset of your system.

*** You may use/modify only for use with the RED REACTOR product
*** Filename: RedReactor_Button.py
*** PythonVn: 3.8, 32-bit
*** Date: May 2021
"""

from gpiozero import Button as GPIOButton  # Used to access pin state
import time  # Used to time the button press

# Constants

# Monitors GPI Button; GPIO-13 is the ON button pin on the 40-pin header
gpio_button = 13

# Used to exit code when button held for reset
hard_reset = False


def button_timer():
    # Called by button GPIO handler to measure button press duration

    global hard_reset

    # Temporarily Stop repeated pressing from calling this function again until it times out
    on_button.when_activated = None

    print("ON Button has been pressed")
    button_state_timer = 0
    print("Button Pressed for:")

    while on_button.is_active:
        print("{} seconds".format(button_state_timer))
        # Wait for 1 second
        time.sleep(1)
        button_state_timer += 1
        if button_state_timer > 10:
            break

    print("Button pressed for {} seconds".format(button_state_timer))

    if button_state_timer < 2:
        print("Short Press detected")
    elif button_state_timer < 3:
        print("Medium Press detected")
    elif button_state_timer < 11:
        print("Long Press detected")
    elif button_state_timer >= 11:
        print("HARD RESET detected, RUN signal would reset system now")
        hard_reset = True

    # Reassign function handler
    on_button.when_activated = button_timer


# Define the pin number and de-bouncing time in seconds
on_button = GPIOButton(gpio_button, bounce_time=0.2)
# Define function to call when button is pressed (default is active low)
on_button.when_activated = button_timer

print("ON button demo")
print(" 0 < Short Press  < 1")
print(" 1 < Medium Press < 3")
print(" 3 < Long Press   < 11")
print(" >= 11 seconds = Hard Reset")
print("Please press the ON button when ready, or CTRL-C to quit")

# Normal project code will simply be interrupted by a button press
# Exit by holding button for 11 seconds or use CTRL-C
try:
    while not hard_reset:
        time.sleep(1)
except KeyboardInterrupt:
    print("Keyboard interrupt - exiting")
