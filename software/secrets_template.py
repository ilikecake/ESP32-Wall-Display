#Device specific configuration entries and passwords. For obvious reasons, don't share this 
#file once you have customized it. Fill out the below info and save this file as 'secrets.py'
#in the same folder as the 'code.py' file.

secrets = {
    #Put your wifi SSID here
    'ssid' : '',
    
    #The password to your wifi goes here
    'password' : '',
    
    #The IP address of your MQTT broker
    'mqtt_broker_ip' : '',
    
    #The port that your MQTT broker listens on. Default is 1883
    'mqtt_broker_port' : '1883',
    
    #The user to use to connect to the MQTT broker.
    'mqtt_broker_user' : '',
    
    #The password to use to connect to the MQTT broker.
    'mqtt_broker_pass' : '',
    
    #Human readable name for this device. This is how it shows up in Homeassistant.
    'device_name' : 'Side Door Display',
    
    #Simplified name of the device. Use only alphanumerics, spaces and special characters 
    #are probably bad. This will be the hostname of the device on the network and the prefix
    #for some of the MQTT topics.
    'device_ID' : 'SideDoorDisplay',
    
    #The MQTT topic to listen for updates to the pixel.
    'device_status_topic' : 'home/status/',
    
    #The MQTT topic of the remote sensor.
    'Remote_Data_Topic' : 'homeassistant/sensor/WeatherStation/state',
    
    #The server or pool to use for NTP time. This can be set to the IP address of a local NTP server
    #or an internet based NTP pool. You can also set it to blank ('') to skip setting time.
    'NTP_ip' : '0.pool.ntp.org',
    
    #Your timezone in hours (+ or -) from GMT
    'timezone' : '-6',
    
    #A unique ID for the device. What you put here is not critical, but it *must* be
    #unique on your network or bad things will happen to your MQTT server. This can be
    #the name of the device, or you can generate a 'real' random UUID from various sources.
    #This UUID will be part of the prefix for the MQTT topics, and will be provided to
    #Homeassistant so that you can properly configure the device.
    'UUID' : '',
    }
