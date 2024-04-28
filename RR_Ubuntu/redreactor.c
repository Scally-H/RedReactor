/*
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 2 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 
 * RED REACTOR - Copyright (c) 2024
 * Author: Pascal Herczog
 * Filename redreactor.c
 * Date: April 2024
 
 */

/* Based heavily on https://git.kernel.org/cgit/linux/kernel/git/stable/linux-stable.git/tree/drivers/power/test_power.c?id=refs/tags/v4.2.6 */


#include <linux/fs.h>
#include <linux/kernel.h>
#include <linux/miscdevice.h>
#include <linux/module.h>
#include <linux/power_supply.h>
#include <linux/init.h>

#include <asm/uaccess.h>

// powersupply contains struct power_supply_desc (incl. fn defs), supplied_to/from and few extended info
// power_supply_property covers all the battery info
// power_supply_propval is int/const char *
static int
redreactor_battery_get_property(struct power_supply *psy,
        enum power_supply_property psp,
        union power_supply_propval *val);

static int
redreactor_ac_get_property(struct power_supply *psy,
        enum power_supply_property psp,
        union power_supply_propval *val);

// Defines battery info
static struct battery_status {
    int status;
    int capacity_level;     // Maps % charge to reporting levels
    int capacity;           // Percentage charge reported by driver
    int microvolts;         // reported by driver
    int microamps;          // reported by driver
    int energyfulldesign;   // reported by driver at initialisation
    int energyfull;         // reported by driver after charging
    int time_left;
} redreactor_battery_status[] = {
    {
        // Sets initial values
        .status = POWER_SUPPLY_STATUS_UNKNOWN,
        // maps % to set of enumarated ranges
        // TBD if this should be UNKNOWN w.r.t. capacity = 100
        .capacity_level = POWER_SUPPLY_CAPACITY_LEVEL_UNKNOWN,
        .capacity = 100,
        
        // Initialise battery voltage to battery nominal voltage, updated by driver
        .microvolts = 3700000,
        // Initialise battery current
        .microamps = 0,

        // Initialise  to 6000mAh * 3700mV = 22.2Wh, updated via driver output
        .energyfulldesign = 6000 * 3700,
        .energyfull = 6000 * 3700,
        
    },
};

/* RR_Driver will update : 1=USB power, 0=Battery */
static int ac_status = 1;

static char *redreactor_ac_supplies[] = {
    "BAT0",
};

// This defines the set of supported properties for RedReactor//
static enum power_supply_property redreactor_battery_properties[] = {
    /* POWER_SUPPLY_PROP_STATUS values can be
        POWER_SUPPLY_STATUS_UNKNOWN = 0,
	    POWER_SUPPLY_STATUS_CHARGING,
	    POWER_SUPPLY_STATUS_DISCHARGING,
	    POWER_SUPPLY_STATUS_NOT_CHARGING,
	    POWER_SUPPLY_STATUS_FULL,
    */
    POWER_SUPPLY_PROP_STATUS,

    /* POWER_SUPPLY_PROP_CHARGE_TYPE values can be
        POWER_SUPPLY_CHARGE_TYPE_UNKNOWN = 0,
        POWER_SUPPLY_CHARGE_TYPE_NONE,      // Not used
        POWER_SUPPLY_CHARGE_TYPE_TRICKLE,	// slow speed at <3v
        POWER_SUPPLY_CHARGE_TYPE_FAST,		// Not used
        POWER_SUPPLY_CHARGE_TYPE_STANDARD,	// normal speed at >3v
        POWER_SUPPLY_CHARGE_TYPE_ADAPTIVE,	// Not used
        POWER_SUPPLY_CHARGE_TYPE_CUSTOM,	// Not used
        POWER_SUPPLY_CHARGE_TYPE_LONGLIFE,	// Not used
    */  
    POWER_SUPPLY_PROP_CHARGE_TYPE,

    /* POWER_SUPPLY_PROP_HEALTH values can be
        POWER_SUPPLY_HEALTH_UNKNOWN = 0,
        POWER_SUPPLY_HEALTH_GOOD,           // OK
        POWER_SUPPLY_HEALTH_OVERHEAT,       // Not used
        POWER_SUPPLY_HEALTH_DEAD,           // Not used
        POWER_SUPPLY_HEALTH_OVERVOLTAGE,    // Vbat > 4.25v
        POWER_SUPPLY_HEALTH_UNSPEC_FAILURE, // Not used
        POWER_SUPPLY_HEALTH_COLD,           // Not used
        POWER_SUPPLY_HEALTH_WATCHDOG_TIMER_EXPIRE,  // Not used
        POWER_SUPPLY_HEALTH_SAFETY_TIMER_EXPIRE,    // Not used
        POWER_SUPPLY_HEALTH_OVERCURRENT,    // If current > 6Amps
        POWER_SUPPLY_HEALTH_CALIBRATION_REQUIRED,   // Not used
        POWER_SUPPLY_HEALTH_WARM,           // Not used
        POWER_SUPPLY_HEALTH_COOL,           // Not used
        POWER_SUPPLY_HEALTH_HOT,            // Not used
    */
    POWER_SUPPLY_PROP_HEALTH,

    // TBC battery present or not
    POWER_SUPPLY_PROP_PRESENT,
    
    // Fixed Value used POWER_SUPPLY_TECHNOLOGY_LION
    POWER_SUPPLY_PROP_TECHNOLOGY,
    
    // TBD should read this from user config via driver?
    // POWER_SUPPLY_PROP_CHARGE_FULL_DESIGN,
    // Changes during battery lifetime not computed
    // POWER_SUPPLY_PROP_CHARGE_FULL,

    // TODO: Try to use this one for initial value and also set PROP_ENERGY_FULL
    // Then use dedicated driver output to only update PROP_ENERGY_FULL
    POWER_SUPPLY_PROP_ENERGY_FULL_DESIGN,

    POWER_SUPPLY_PROP_ENERGY_FULL,  // Value read from driver in uWh
    
    POWER_SUPPLY_PROP_CHARGE_NOW,   // Value read from driver (% charge)

    // What is this one? Is it mWh? or uWh? or?
    // Doesn't work without it but not sure if it works with it!
    POWER_SUPPLY_PROP_CAPACITY,

    /* Default value unknown, but set to 10%*/
    POWER_SUPPLY_PROP_CAPACITY_ALERT_MIN, /* in percents! */
	
    /* POWER_SUPPLY_PROP_CAPACITY_LEVEL values used
        POWER_SUPPLY_CAPACITY_LEVEL_UNKNOWN = 0,
        POWER_SUPPLY_CAPACITY_LEVEL_CRITICAL,
        POWER_SUPPLY_CAPACITY_LEVEL_LOW,
        POWER_SUPPLY_CAPACITY_LEVEL_NORMAL,
        POWER_SUPPLY_CAPACITY_LEVEL_HIGH,
        POWER_SUPPLY_CAPACITY_LEVEL_FULL,
    */
    POWER_SUPPLY_PROP_CAPACITY_LEVEL,

    // seems to be computed from battery power vs. capacity
    // I was unable to make Ubuntu use driver supplied data!
    // POWER_SUPPLY_PROP_TIME_TO_EMPTY_NOW,

    // seems to be computed from battery power vs. capacity
    // I was unable to make Ubuntu use driver supplied data!
    // POWER_SUPPLY_PROP_TIME_TO_FULL_NOW,
    
    POWER_SUPPLY_PROP_MODEL_NAME,
    POWER_SUPPLY_PROP_MANUFACTURER,
    POWER_SUPPLY_PROP_SERIAL_NUMBER,
    // POWER_SUPPLY_PROP_TEMP, // not used
    
    POWER_SUPPLY_PROP_VOLTAGE_NOW,  // Value read from driver in uV
	POWER_SUPPLY_PROP_CURRENT_NOW,  // Value read from driver in uA
};

static enum power_supply_property redreactor_ac_properties[] = {
    POWER_SUPPLY_PROP_ONLINE,
};

static struct power_supply_desc descriptions[] = {
    {
        .name = "BAT0",
        .type = POWER_SUPPLY_TYPE_BATTERY,
        .properties = redreactor_battery_properties,
        .num_properties = ARRAY_SIZE(redreactor_battery_properties),
        .get_property = redreactor_battery_get_property,
    },

    {
        .name = "AC0",
        .type = POWER_SUPPLY_TYPE_MAINS,
        .properties = redreactor_ac_properties,
        .num_properties = ARRAY_SIZE(redreactor_ac_properties),
        .get_property = redreactor_ac_get_property,
    },
};

static struct power_supply_config configs[] = {
    // TBD what these blanks are
    { },
    { },
    {
        .supplied_to = redreactor_ac_supplies,
        .num_supplicants = ARRAY_SIZE(redreactor_ac_supplies),
    },
};

// creates array size 2 of that contains description, supplied to, supplied from
static struct power_supply *supplies[sizeof(descriptions) / sizeof(descriptions[0])];

// Called when /dev/redreactor is read from by user
// No data output - user should read /sys/class/power_supply folder
static ssize_t
control_device_read(struct file *file, char *buffer, size_t count, loff_t *ppos)
{
    // This is what shows up on reading the /dev/redreactor file
    static char *message = "Redreactor device driver file!";
    size_t message_len = strlen(message);

    if(count < message_len) {
        return -EINVAL;
    }

    if(*ppos != 0) {
        return 0;
    }

    if(raw_copy_to_user(buffer, message, message_len)) {
        return -EINVAL;
    }

    *ppos = message_len;

    return message_len;
}

#define prefixed(s, prefix)\
    (!strncmp((s), (prefix), sizeof(prefix)-1))

// called for each line from /dev/redreactor to decode entry
static int
handle_control_line(const char *line, int *ac_status, struct battery_status *batteries)
{
    char *value_p;
    int value;
    int status;
	
	// pr_info("RR: Handle Control Line called\n");

    value_p = strchrnul(line, '=');

    if(!value_p) {
        return -EINVAL;
    }

    value_p = skip_spaces(value_p + 1);
    status = kstrtoint(value_p, 10, &value);

    if(status) {
        return status;
    }

    /* Valid lines are
    microvolts = 4200000
    microamps = 2300000
    capacity = 100
    energydesignfull = 22300000
    energyfull = 21000000

    // microvolts range 2800000 to 4250000
    // microamps range -1200000 to 6000000
    // capacity range 0 to 100
    */

    // pr_info("RR: reading /dev = %s\n", line);

    if(prefixed(line, "microvolts")) {
        batteries[0].microvolts = value;
        // pr_info("RR: Battery Micro Volts = %i\n", value);

    } else if(prefixed(line, "microamps")) {
        batteries[0].microamps = value;
        // pr_info("RR: Battery Micro Amps = %i\n", value);

        // <10000uA implies external power, report changes to system log
        if (value < 10000) {
            *ac_status = 1;
            // pr_info("RR: Battery AC Status = True");
        } else {
            *ac_status = 0;
            // pr_info("RR: Battery AC Status = False");
        }

    // Driver computes capacity based on battery model
    } else if(prefixed(line, "capacity")) {
        batteries[0].capacity = value;
        // pr_info("RR: Battery Capacity = %i\n", batteries[0].capacity);
    }  else if(prefixed(line, "energyfulldesign")) {
        // Initialise both properties on startup
        batteries[0].energyfulldesign = value;
        batteries[0].energyfull = value;
        // Only gets logged once
        pr_info("RR: Energy Full Design = %i\n", batteries[0].energyfulldesign);
    } else if(prefixed(line, "energyfull")) {
        // Update end of charge full value
        batteries[0].energyfull = value;
        // Log each time charge full reached
        pr_info("RR: Energy Full = %i\n", batteries[0].energyfull);
    } else {
        return -EINVAL;
    }

    return 0;
}

static void
handle_charge_changes(int ac_status, struct battery_status *battery)
{
    // pr_info("RR: Handle Charge Changes called\n");
	
	if(ac_status) {
        if(battery->microamps < 0) {
            battery->status = POWER_SUPPLY_STATUS_CHARGING;
        } else {
            battery->status = POWER_SUPPLY_STATUS_FULL;
        }
    } else {
        battery->status = POWER_SUPPLY_STATUS_DISCHARGING;
    }

    if(battery->capacity >= 98) {
        battery->capacity_level = POWER_SUPPLY_CAPACITY_LEVEL_FULL;
    } else if(battery->capacity_level >= 70) {
        battery->capacity_level = POWER_SUPPLY_CAPACITY_LEVEL_HIGH;
    } else if(battery->capacity_level >= 30) {
        battery->capacity_level = POWER_SUPPLY_CAPACITY_LEVEL_NORMAL;
    } else if(battery->capacity_level >= 5) {
        battery->capacity_level = POWER_SUPPLY_CAPACITY_LEVEL_LOW;
    } else {
        battery->capacity_level = POWER_SUPPLY_CAPACITY_LEVEL_CRITICAL;
    }

}

// Called when /dev/redreactor is written to by redreactor RR_Driver
static ssize_t
control_device_write(struct file *file, const char *buffer, size_t count, loff_t *ppos)
{   
    char kbuffer[256]; /* limited by kernel frame size, 256bytes should be enough */
    char *buffer_cursor;
    char *newline;
    size_t bytes_left = count;

    int status;
	
	// pr_info("RR: Control Device Write called\n");

    if(*ppos != 0) {
        printk(KERN_ERR "writes to /dev/redreactor must be completed in a single system call\n");
        return -EINVAL;
    }

    if(count > 256) {
        printk(KERN_ERR "Too much data provided to /dev/redreactor (limit 256 bytes)\n");
        return -EINVAL;
    }

    status = raw_copy_from_user(kbuffer, buffer, count);

    if(status != 0) {
        printk(KERN_ERR "bad copy_from_user\n");
        return -EINVAL;
    }

    buffer_cursor = kbuffer;
    // pr_info("RR: /dev/redreactor status OK, check entries\n");

    // Call handle_control_line to decode each line from /dev/redreactor
    while((newline = memchr(buffer_cursor, '\n', bytes_left))) {
        *newline = '\0';
        
        // Debug to see what lines are read in
        // pr_info("RR: /dev/redreactor line = %s\n", buffer_cursor);
        
        /* XXX this is non-atomic */
        status = handle_control_line(buffer_cursor, &ac_status, redreactor_battery_status);

        if(status) {
            return status;
        }

        bytes_left    -= (newline - buffer_cursor) + 1;
        buffer_cursor  = newline + 1;
    }

    // Assigns further battery status values
    handle_charge_changes(ac_status, &redreactor_battery_status[0]);

    // [0] = BAT0, [1]=AC0
    power_supply_changed(supplies[0]);
    power_supply_changed(supplies[1]);

    return count;
};

/* This defines functions to call when /dev/redreactor is written to or read from */
static struct file_operations control_device_ops = {
    .owner = THIS_MODULE,
    // call this function when /dev/redreactor is read from
    // just report as red reactor driver file, no data
    .read = control_device_read,
    // call this function when /dev/redreactor is written to
    .write = control_device_write,
};

/* This defines the device name and file ops list */
static struct miscdevice control_device = {
    // Character device
    MISC_DYNAMIC_MINOR,
    // creates the /dev/redreactor device file
    "redreactor",
    // links the device file operations to function callbacks
    &control_device_ops,
};

// called from redreactor_battery_get_property
static int
redreactor_battery_generic_get_property(struct power_supply *psy,
        enum power_supply_property psp,
        union power_supply_propval *val,
        struct battery_status *status)
{
	switch (psp) {
        case POWER_SUPPLY_PROP_MANUFACTURER:
            val->strval = "RedReactor";
            break;
        case POWER_SUPPLY_PROP_STATUS:
            // Charging / Full / Discharging
            // pr_info("RR: PROP_STATUS = %d", status->status);
            val->intval = status->status;
            break;
        case POWER_SUPPLY_PROP_CHARGE_TYPE:
            // TODO: set to TRICKLE if voltage < 3V
            // pr_info("RR: PROP_CHRGTYPE = %d", POWER_SUPPLY_CHARGE_TYPE_STANDARD);
            val->intval = POWER_SUPPLY_CHARGE_TYPE_STANDARD;
            break;
        case POWER_SUPPLY_PROP_HEALTH:
            // TODO: use bat fault to show bad health
            // pr_info("RR: PROP_HEALTH = %d", POWER_SUPPLY_HEALTH_GOOD);
            val->intval = POWER_SUPPLY_HEALTH_GOOD;
            break;
        case POWER_SUPPLY_PROP_PRESENT:
            // TODO: set to 0 if INA read fault
            // pr_info("RR: PROP_PRESENT = 1");
            val->intval = 1;
            break;
        case POWER_SUPPLY_PROP_TECHNOLOGY:
            // pr_info("RR: PROP_TECH = %d", POWER_SUPPLY_TECHNOLOGY_LION);
            val->intval = POWER_SUPPLY_TECHNOLOGY_LION;
            break;
        case POWER_SUPPLY_PROP_CAPACITY_ALERT_MIN:
            // Currently hardcoded to 10%; TODO - allow user defined value / change
            // pr_info("RR: PROP_CAPACITY_ALERT_MIN = 10%%");
            val->intval = 10;
            break;
        case POWER_SUPPLY_PROP_CAPACITY_LEVEL:
            // Mapped full, high, normal, low, critical based on capacity
            // pr_info("RR: PROP_CAPACITY_LEVEL = %d", status->capacity_level);
            val->intval = status->capacity_level;
            break;
        case POWER_SUPPLY_PROP_CAPACITY:
            // Falls through to the next case, sets PROP_CAPACITY to capacity %
        case POWER_SUPPLY_PROP_CHARGE_NOW:
            // read from /dev/redreactor as percentage
            // pr_info("RR: PROP_CHARGE_NOW = %d %%", status->capacity);
            val->intval = status->capacity;
            break;
        // TBC if useful, using ENERGY properties instead
        // case POWER_SUPPLY_PROP_CHARGE_FULL_DESIGN:
            // pr_info("RR: PROP CHRG FULL DESIGN = %d", status->chargefulldesign);
            // val->intval = status->chargefulldesign;
            // break;
        // case POWER_SUPPLY_PROP_CHARGE_FULL:
            // pr_info("RR: PROP CHRG FULL = %d", status->chargefulldesign);
            // val->intval = status->chargefulldesign;
            // break;
        case POWER_SUPPLY_PROP_ENERGY_FULL_DESIGN:
            // read from /dev/redreactor as uWh value only during start-up
            // pr_info("RR: PROP ENERGY FULL DESIGN = %d uWh", status->energyfulldesign);
            val->intval = status->energyfulldesign;
            break;
        case POWER_SUPPLY_PROP_ENERGY_FULL:
            // read from /dev/redreactor as uWh value, updated at each charge cycle
            // pr_info("RR: NEW PROP ENERGY FULL = %d uWh", status->energyfull);
            val->intval = status->energyfull;
            break;
        case POWER_SUPPLY_PROP_VOLTAGE_NOW:
            // retrieved from /dev/redreactor in uV
            // pr_info("RR: Assigning MicroVolts = %d\n", status->microvolts);
            val->intval = status->microvolts;
            break;
		case POWER_SUPPLY_PROP_CURRENT_NOW:
            // retrieved from /dev/redreactor in uA, force positive for reporting
            // pr_info("RR: Assigning MicroAmps = %d\n", status->microamps);
		    val->intval = abs(status->microamps);
			break;
        
        default:
            pr_info("RR: %s: some properties deliberately report errors: %d\n",
                    __func__, psp);
            return -EINVAL;
    }
    return 0;
};

static int
redreactor_battery_get_property(struct power_supply *psy,
        enum power_supply_property psp,
        union power_supply_propval *val)
{
	switch (psp) {
        case POWER_SUPPLY_PROP_MODEL_NAME:
            val->strval = "RedReactor PSU";
            break;
        case POWER_SUPPLY_PROP_SERIAL_NUMBER:
            val->strval = "20240427";
            break;
        default:
			// All other property assignments
            return redreactor_battery_generic_get_property(psy, psp, val, &redreactor_battery_status[0]);
    }
    return 0;
}

static int
redreactor_ac_get_property(struct power_supply *psy,
        enum power_supply_property psp,
        union power_supply_propval *val)
{
	switch (psp) {
    case POWER_SUPPLY_PROP_ONLINE:
            val->intval = ac_status;
			// pr_info("RR: AC get property status = %d\n", ac_status);
            break;
    default:
            return -EINVAL;
    }
    return 0;
}

// Install RR_Kernel module
static int __init
redreactor_battery_init(void)
{
    int result;
    int i;

    result = misc_register(&control_device);
    if(result) {
        printk(KERN_ERR "Unable to register misc device!");
        return result;
    }

    for(i = 0; i < ARRAY_SIZE(descriptions); i++) {
        supplies[i] = power_supply_register(NULL, &descriptions[i], &configs[i]);
        if(IS_ERR(supplies[i])) {
            printk(KERN_ERR "Unable to register power supply %d in redreactor_battery\n", i);
            goto error;
        }
    }

    printk(KERN_INFO "loaded redreactor_battery module\n");
    return 0;

error:
    while(--i >= 0) {
        power_supply_unregister(supplies[i]);
    }
    misc_deregister(&control_device);
    return -1;
}

// Uninstall RR_Kernel module
static void __exit
redreactor_battery_exit(void)
{
    int i;

    misc_deregister(&control_device);

    for(i = ARRAY_SIZE(descriptions) - 1; i >= 0; i--) {
        power_supply_unregister(supplies[i]);
    }

    printk(KERN_INFO "unloaded redreactor_battery module\n");
}

module_init(redreactor_battery_init);
module_exit(redreactor_battery_exit);

MODULE_LICENSE("GPL");
MODULE_AUTHOR("Pascal Herczog");
MODULE_DESCRIPTION("RedReactor Kernel Module");
MODULE_VERSION("1.01");