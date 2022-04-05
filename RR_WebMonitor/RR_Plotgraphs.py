#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
*** RED REACTOR - Copyright (c) 2022
*** Author: Pascal Herczog

*** This code is designed for the RED REACTOR Raspberry Pi Battery Power Supply
*** Example code provided without warranty
*** Creates a x-y plot image for use with RR_WebMonitor.py as web page application

# Input is lists of Y1 (Volts), Y2 (mA), Temp : length defines number of samples
# Min-max are fixed based on the RedReactor specifications

*** You may use/modify only for use with the RED REACTOR product
*** Filename: RR_Plotgraphs.py
*** PythonVn: 3.8, 32-bit
*** Date: April 2022
"""

# Import Libraries
import numpy as np
import matplotlib.pyplot as plt

# Only show plot if used stand-alone
show_plot = False


def rr_plots(y1: list, y2: list, temperature: list):
    """Plots graphs to image file for RR_WebMonitor
    :param
    y1 = list of voltage samples
    y2 = list of current samples
    temperature = list of temperature samples on separate plot

    All lists assumed to be the same length (= number of samples)
    """

    print("RR_Plotgraphs : Plotting samples:", len(y1))
    x1data = np.arange(len(y1))
    y1data = np.array(y1)
    y2data = np.array(y2)
    t1data = np.array(temperature)

    # Create Plot space
    fig, (ax1, ax3) = plt.subplots(nrows=2, ncols=1, gridspec_kw={'height_ratios': [2, 1]})

    # Main Title
    ax1.set_title('RedReactor Battery Monitor Status', fontdict={'fontweight': 'bold'})

    # Main plot for voltage and current
    ax1.set_xlabel('Time (samples)')
    ax1.set_ylabel('Voltage (V)', color='black')
    # -o to plot marker and line
    line1 = ax1.plot(x1data, y1data, '-o', color='red', label='Volts (V)')

    ax1.tick_params(axis='y', labelcolor='black')

    # Set up 2nd y-axis
    ax2 = ax1.twinx()
    ax2.set_ylabel('Current (mA)', color='blue')
    # -o to plot marker and line
    line2 = ax2.plot(x1data, y2data, '-o', color='blue', label='Current (mA)')
    ax2.tick_params(axis='y', labelcolor='blue')

    # Set x-axis tick interval to scale with dataset
    ax1.set_xticks(np.arange(min(x1data), max(x1data) + int(max(x1data)/10)+1,
                             int((max(x1data)/10)+1) if max(x1data) > 10 else 1))

    # Set y1-axis limits for fixed sized graph
    ax1.set_ylim([2.4, 4.3])
    # For current, set y2-axis max scale according to simple usage models
    if min(y2data) < 0:
        y_min = -1500
    else:
        y_min = 0
    if max(y2data) < 500:
        y_max = 500
    else:
        y_max = max(y2data)//1000*1000+1000
    ax2.set_ylim([y_min, y_max])

    # Combine labels, lower left is best overall
    lines = line1 + line2
    labels = [lab.get_label() for lab in lines]
    plt.legend(lines, labels, loc='lower left', fontsize='small', fancybox=True, framealpha=1, shadow=True, borderpad=1)

    # Temperature plot
    ax3.set_xlabel('Time (samples)')
    ax3.set_ylabel('Temp (degrees)', color='orange')
    # -o to plot marker and line
    ax3.plot(x1data, t1data, '-o', color='orange', label='Temp (C)')

    # Set x-axis tick interval
    ax3.set_xticks(np.arange(min(x1data), max(x1data) + int(max(x1data)/10)+1,
                             int((max(x1data)/10)+1) if max(x1data) > 10 else 1))
    # Set y-axis limits for fixed sized graph
    ax3.set_ylim([0, 100])

    # labelright copies y1 scale to y2
    ax3.tick_params(axis='y', labelcolor='red', labelright=True)

    ax3.legend(loc='upper left', fontsize='small', fancybox=True, framealpha=1, shadow=True, borderpad=1)

    # Tidy up display of graphs (ensure they fit and have spacing between)
    fig.set_size_inches(5, 6)
    fig.tight_layout()

    # Save (and Show plot for testing) (order important)
    plt.savefig('RR_Status.png', bbox_inches='tight', dpi=100)
    if show_plot:
        plt.show()

    # Allow it to be garbage collected
    plt.close(fig)


# Test rr_plots function
if __name__ == "__main__":
    print("RR_Plotgraphs : Testing plot function with example data")
    show_plot = True

    x = np.arange(0, 15, 0.2)

    # Lengths should be the same
    history_volts = [4.2, 4.1, 4.0, 3.9, 3.8, 3.7, 3.6, 3.5, 3.4, 3.3,
                     3.2, 3.2, 3.1, 3.0, 2.9, 3.2, 3.5, 4.0, 4.2]
    history_milli = [1.0, 1400, 1200, 1500, 1800, 1250, 1000, 900, 600, 500,
                     500, 800, 900, 800, 1700, -1000, -400, -250, 2]
    history_temp = [33.5, 38, 45, 50, 55.5, 60, 63.2, 68.9, 74, 65.1,
                    55.9, 52, 65, 69, 78, 61.9, 45, 40, 38]

    # Expected to have same lengths in normal use
    print("RR_Plotgraphs : volts samples", len(history_volts))
    print("RR_Plotgraphs : milli samples", len(history_milli))
    print("RR_Plotgraphs : temp samples", len(history_temp))

    rr_plots(history_volts, history_milli, history_temp)
