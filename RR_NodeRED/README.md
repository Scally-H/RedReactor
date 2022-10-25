<H1>Red Reactor Node-RED Dashboard</H1>

We're pleased to announce the release of our Node-RED Home Automation Dashboard, 
which connects to our RR_MQTT client and gives you full visibility and control 
of your Red Reactor enabled Pi system!

<img src="RR_NodeRED UI Screenshot.JPG" width="75%"  alt="The Red Reactor Node-RED Dashboard" title="Red Reactor Node-RED Dashboard">

<H2> Red Reactor Dashboard Features </H2>

The Dashboard UI provides you full visibility of your power status, confguration and system control:

The dashboard is divided into 3 groups of information:

1. Battery charge, along with voltage and current history graphs
2. Battery status, with simple views on battery versus USB power activity, CPU status and detailed battery statistics
3. Battery configuration, with sliders to adjust reporting interval, warning and shutdown levels

Along with buttons for REBOOT and SHUTDOWN, the Red Reactor flow will actively monitor the conditions and provide pop-up warnings as certain status elements change, such as loss/restoration of external power, as well as battery low and imminent shutdown info.

The configuration sliders allow you to adjust the settings, and when updated by the RR_MQTT client the new values are reported back for confirmation of status. Note that this happens at the next reporting interval.

The CPU status provides an easy to use decoded text about throttling conditions, with a mouse pop-up to explain the status fields.

Using all features of the RR_MQTT client, the information is updated at the reporting interval, and immediately when RR_MQTT detects critical changes such as external power loss.

<H2> Installing the Red Reactor Dashboard </H2>

Please follow the instructions for our RR_MQTT client to install RR_MQTT on your Red Reactor Pi. You will also need an MQTT Broker, such as Mosquito.

Instructions on how to install Node-RED, for example on Windows, can be found here https://nodered.org/docs/getting-started/windows . For this you also first need to install node.js, just be sure to turn off your anti-virus during the install as we found it blocked unzipping some of its files.

The Red Reactor Dashboard is built with nodes from the node-red-dashboard component, which you need to install from within Node Red - go to User Settings / Palette / Install and search for node-red-dashboard. It also uses a media display node, for which you need to install node-red-contrib-ui-media.

Then you can import the Red Reactor Dashboard UI by using the IMPORT function. Inside the Red Reactor Dashboard flow you need to configure the hostname of your Red Reactor setup so that the Dashboard can connect to the correct MQTT topics as defined by <hostname>/RedReactor/topic_name, where hostname is taken either directly from your Pi or via the RR_MQTT's config.yaml file.

You will also need to configure and connect the MQTT nodes to your instance of the MQTT Broker, having configured the MQTT Broker's IP address in your Node-RED global configuration nodes list.


Then simply deploy the dashboard for access via your browser!


<H2> Using the Red Reactor Dashboard </H2>

After deploying the Red Reactor Dashboard, you can check that Node-RED has successfully connected to your MQTT broker in its command window. With the Mosquito MQTT Broker, starting it with the -v option gives you good debug feedback about devices and Node Red connections in its own command window.

Then, check that the hostname in the top left of the UI matches that of your Red Reactor setup, and if correct you will see that the RR_Status should show ON (this is the on-line string as defined by your RR_MQTT config.yaml file).

The configuration sliders can be moved to change their respective parameter values on the fly. The new value is sent on releasing the mouse button and at the next reporting interval the RR_MQTT client will cause the reported values to be updated.

If the CPU is experiencing, or has experienced throttling conditions, this will be reflected in the flags shown with CPU Status. A tooltip will show up when you hovver your mouse pointer over the status field.

When the battery warning level is reached the Red Reactor Dashboard will create a pop-up as a warning. The set percentage is a function of 4.2v - VMIN. You may wish to change both the warning level and VMIN, for example, when operating under high-temperature and/or high-current conditions. It would also be possible to automate such a change by adding a function to the Red Reactor flow in Node Red.


<H2>HELP!</H2>

If you have any problems installing this application please send us a message on support@theredreactor.com and we'll be sure to help!

<H2>Where can I get a Red Reactor?</H2>
We are now live on Kickstarter!
So please visit us at https://www.kickstarter.com/projects/pascal-h/the-red-reactor-when-power-really-matters for some great options!
 
