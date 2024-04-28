/*

*** RED REACTOR - Copyright (c) 2024
*** Author: Pascal Herczog

*** This code is designed for the RED REACTOR Raspberry Pi Battery Power Supply
*** Example code provided without warranty
*** Red Reactor device driver for Ubuntu ACPI battery status

*** You may use/modify only for use with the RED REACTOR product
*** Filename: RR-Driver.cc
*** C++: g++ for Ubuntu 22.04LTS
*** Date: April 2024

*** use make to compile this driver
*** ina219 source modified from https://github.com/regisin/ina219

*/

#include <iostream> // std::cout
#include <fstream>  // std::ofstream
#include <signal.h> // added for ctrl-c in dev
#include <stdlib.h> // added for ctrl-c
#include <syslog.h>
#include <unistd.h>
#include <math.h>
#include <map>
#include "src/ina219.h"

// For interactive testing output to terminal, use: make debug
#ifdef DEBUG
#define DEBUG_STDOUT(x) do { std::cout << x << std::endl; } while (0)
#else 
#define DEBUG_STDOUT(x)
#endif

const float INTERVAL = 1000.0;  // Sample interval, in ms
const int SAMPLES = 10;         // Sampling average, must be >1
const int REPORT = 5;           // # of Intervals for report update unless power change

const float SHUNT_OHMS = 0.05;      // Fixed for RedReactor
const float MAX_EXPECTED_AMPS = 6.4;
const float BATTERY_VMAX = 4.2;
const float BATTERY_COVR = 0.025;   // Charging VMAX delta for capacity calc
const float BATTERY_VMIN = 2.9;     // Increase this to force earlier shutdown

//Edit if using different 18650 battery capacity
#define BATSIZE 6000            //Capcity mAh total

// Write data to device driver file
const char *outputFile = "/dev/redreactor";

struct avSamples {
    // float is sufficient accuracy
    float voltage;
    float current;
    float last_v; // track for charge->full changes
} avResults;

// Calculate Voltage and Current Averages
void sampleAverages(float newVoltage, float newCurrent) {
    // Static preserves values between calls
    // First call initialises av to input values, after (N-1)/N old + 1/N new
    // Hold averaged values for voltage and current
    // Keep last sample for board chrg_vmax

    static float av_V = newVoltage;
    static float av_A = newCurrent;
    static float v_sample = newVoltage;

    // TODO: MESSY with av reset in main() too - SORT where is best
    // TODO: check here if avcurrent < 10 and the suddenly > 10 to improve first averaging sample?

    // Reset averaging on current flow change chrg->(full | dis)->chrg
    if ((bool)signbit(newCurrent) != (bool)signbit(av_A)) {
        av_A = newCurrent;
    }
    
    // Reset average if full -> discharge
    if ((avResults.current < 10) && (newCurrent > 10)) {
        av_A = newCurrent;
    } else {
        av_A = av_A * (SAMPLES-1)/SAMPLES + newCurrent / SAMPLES;
    }

    av_V = av_V * (SAMPLES-1)/SAMPLES + newVoltage / SAMPLES;
    
    // cout << "V=" << av_V << " A=" << av_A << endl;

    // Provide results
    avResults.voltage = av_V;
    avResults.current = av_A;
    avResults.last_v = v_sample;
    v_sample = newVoltage;

}

void my_handler(sig_atomic_t s) {
           std::cout << "Abort Signal " << s << std::endl;
           syslog(LOG_INFO, "RR-Driver aborting");
           closelog();
           exit(0);

}

int main()
{
    /* Runs RR-Driver and writes data to /dev/redreactor
    */

    // Create logger
    openlog ("RedReactor", LOG_CONS | LOG_PID | LOG_NDELAY, LOG_LOCAL1);
    syslog (LOG_INFO, "RR-Driver started");

    // Detect abort signal (incl. CTRL-C)
    signal (SIGINT, my_handler);
    
    // Log main events [start, charging -> full -> discharging -> empty -> shutdown]
    enum batStates {
        start, charging, full, discharging, low
    } batState = start, newBatState = start;

    // Create a mapping from batState enum values to corresponding strings for log
    std::map<batStates, std::string> stateToString = { { start,     "Starting" },
                                                        { charging, "Charging" }, 
                                                        { full,     "FULL" },
                                                        { discharging, "Discharging"},
                                                        { low,      "LOW!"} };

    int capacity = 100;             // driver computes capacity %
    float full_vmax = BATTERY_VMAX; // will update at end of each charge cycle
    float last_full_vmax = full_vmax;
    float chrg_vmax = BATTERY_VMAX; // will update at end of each charge cycle
    float last_chrg_vmax = chrg_vmax;

    // Define initial available battery energy when full (uWh)
    int energy_full = BATSIZE * (int)((BATTERY_VMIN + (BATTERY_VMAX - BATTERY_VMIN)/2) * 1000);

    // Limit decimal places in debug text
    std::cout.setf(std::ios::fixed);
    std::cout.setf(std::ios::showpoint);
    std::cout.precision(3);


    // Configure Red Reactor Board and run monitoring loop

    // Initialise IN219 Battery Monitor class
    INA219 redreactor(SHUNT_OHMS, MAX_EXPECTED_AMPS);

    // Configure for Red Reactor Board
    // ADDRESS is default 0x40, bus=1
    // RANGE_16V for 0-5v measured values
    // GAIN_8_320mv for 0.05 Ohms at 6.4 Amps max
    // ADC_12BIT for 12-bit conversion time 532us of bus_adc, shunt_adc
    redreactor.configure(RANGE_16V, GAIN_8_320MV, ADC_12BIT, ADC_12BIT);

    // Send initial status to /dev/redreactor
    // Write battery energy when full to device driver file in uWh
    // Value will be updated when board specific Vbat after charging is known
    // As battery deteriorates this Vbat will also lower energy full reported
    DEBUG_STDOUT("Energy Full Design (uWh) = " << energy_full);
    syslog(LOG_INFO, "Original Battery Capacity (Wh) = %.3f", (float)energy_full / (1000 * 1000));

    std::ofstream deviceFile (outputFile, std::ofstream::out);
    if (deviceFile.is_open()) {
        deviceFile << "energyfulldesign = " << energy_full << std::endl;
        deviceFile.close();
    } else {
        DEBUG_STDOUT("Unable to open and write initialisation to device file");
        syslog(LOG_ERR, "RR-Driver Unable to write initialisation to device file");
    }
    
    // Start loop to monitor battery
    DEBUG_STDOUT("time_s\tV_Sup\tA_mA\tV_av\tA_av\tCap\tC-Vmax\tF-Vmax");
    int sample = 0;
    while (true)
    {
        float voltage = redreactor.supply_voltage();
        // Positive = discharge, Negative = Charge
        // Note, values <=10mA are at Battery FULL, >10mA is no external power
        float current = redreactor.current();
        // Updates avResults
        sampleAverages(voltage, current);
        
        if (current < 0) {
            newBatState = charging;
            // compute capacity level for charging state based on fully charged vmax for this board
            // add margin to avoid going negative
            capacity = (int)((avResults.voltage - BATTERY_VMIN) / (chrg_vmax + BATTERY_COVR - BATTERY_VMIN) * 100);
        } else
            if (current < 10) {
                newBatState = full;
                // On reaching full set to capacity 100%
                if (batState != newBatState) {
                    capacity = 100;

                    if ( batState != start) {
                        // End of normal charge cycle

                        // Track board specific charge vmax
                        last_chrg_vmax = chrg_vmax;
                        chrg_vmax = avResults.last_v;
                        DEBUG_STDOUT("Updating charge Vmax to " << chrg_vmax);
                       
                        // Track battery specific idle full vmax
                        last_full_vmax = full_vmax;
                        full_vmax = voltage;
                        DEBUG_STDOUT("Idle FULL Volts =" << full_vmax);
                    }

                    // Reset averages as now full
                    avResults.voltage = voltage;
                    avResults.current = current;
                    
                } else {
                    // 100% allows small reduction whilst fully charged
                    capacity = (int)((avResults.voltage - BATTERY_VMIN) / (full_vmax - BATTERY_COVR - BATTERY_VMIN) * 100);
                }
            } else {
                newBatState = discharging;
                // Use vmax at idle full state minus variation to compute capacity
                capacity = (int)((avResults.voltage - BATTERY_VMIN) / (full_vmax - BATTERY_COVR - BATTERY_VMIN) * 100);
            }

        // Manage rounding errors
        if (capacity > 100) {
            capacity = 100;
        } else if (capacity < 0) {
            capacity = 0;
        }
        
        // Use this to see every sample
        // DEBUG_STDOUT((roundf(sample*(INTERVAL/1000.0) * 1000) / 1000) << "\t"
        //              << (roundf(voltage * 100000) / 100000) << "\t"
        //              << (roundf(current * 1000) / 1000) << "\t"
        //              << avResults.voltage << "\t" << avResults.current << "\t"
        //              << capacity << "\t" << chrg_vmax << "\t" << full_vmax);
        
        if ((newBatState == discharging) && (avResults.voltage < BATTERY_VMIN + 0.1)) {
            newBatState = low;
        }

        if (batState != newBatState) {
            batState = newBatState;
            // map state to string
            std::string msgUpdate = "BATTERY IS " + stateToString[batState];
            DEBUG_STDOUT(msgUpdate);
            syslog(LOG_INFO, "%s", msgUpdate.c_str());
            // Force new report immediately
            sample = 0;
        }


        if (sample % REPORT == 0) {
            // Output new results
            DEBUG_STDOUT("REPORT " << sample);

            DEBUG_STDOUT((roundf(sample*(INTERVAL/1000.0) * 1000) / 1000) << "\t"
                    << (roundf(voltage * 100000) / 100000) << "\t"
                    << (roundf(current * 1000) / 1000) << "\t"
                    << avResults.voltage << "\t" << avResults.current << "\t"
                    << capacity << "\t" << chrg_vmax << "\t" << full_vmax);

            // Include energy update if idle vmax reduced by 0.01v at end of last charge cycle
            std::string update = "microvolts = " + std::to_string((int)(avResults.voltage * 1000 * 1000)) + "\n" +
                                "microamps = " + std::to_string((int)(avResults.current * 1000)) + "\n" +
                                "capacity = " + std::to_string(capacity);
            if (full_vmax < last_full_vmax - 0.01) {
                energy_full = BATSIZE * (int)((BATTERY_VMIN + (full_vmax - BATTERY_VMIN)/2) * 1000);
                update += (std::string)"\nenergyfull = " + std::to_string(energy_full);
                last_full_vmax = full_vmax;
                syslog(LOG_INFO, "Updated Battery Capacity (Wh) = %.3f", (float)energy_full / (1000 * 1000));
            }

            DEBUG_STDOUT(update);

            // Write report to device driver file in micro volts/amps
            std::ofstream deviceFile (outputFile);
            if (deviceFile.is_open()) {
                deviceFile << update << std::endl;
                deviceFile.close();
            } else {
                DEBUG_STDOUT("Unable to open and write to device file");
                syslog(LOG_ERR, "RR-Driver Unable to write to device file");
            }

            sample = 0;
        }

        if (avResults.voltage <= BATTERY_VMIN) {
            // Force system shutdown
            DEBUG_STDOUT("RR-Driver Forcing SHUTDOWN");
            syslog (LOG_CRIT, "RR-Driver Battery Empty - Forcing Shutdown now");
            // Use system command
            closelog();
            system("shutdown now");
            break;
        }

        // Optional: use redreactor.sleep() and redreactor.wake()
        usleep(INTERVAL * 1000);

        sample++;

    }

    DEBUG_STDOUT("RR-Driver FINISHED");
    syslog(LOG_INFO, "RR-Driver exited");
    closelog();
    // Note, Kernel stays loaded across power cycles

	return 0;
}
