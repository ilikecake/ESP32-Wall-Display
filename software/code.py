import json
import time
import board
import digitalio
import rtc
import displayio
import weather_display
import adafruit_ntp
import countio
import microcontroller

import ipaddress
import ssl
import wifi
import socketpool
import adafruit_requests
import neopixel

from adafruit_bme280 import basic as adafruit_bme280
import adafruit_minimqtt.adafruit_minimqtt as MQTT

#Clear any old display data
displayio.release_displays()

TIMEOUT_COUNTS = 200    #How many times to try connecting to Wifi and MQTT before reset.
RETRY_DELAY = 30        #How long to wait between retries of wifi and MQTT connection. Note that the connect functions also have delay built in, so real delay will be longer than this.
NTP_Time_Set = False    #Set to True when a valid time was recieved from NTP

#Global pixel data. The pixel is used during initialization to indicate the status.
#   - Red:      Connecting to wifi
#   - Blue:     Connectingn to MQTT broker
#   - White:    Getting time from NTP
#   - Yellow:   Network error in main loop, reconnecting.
#Once the device is initialized, the pixel is controlled by the MQTT broker.
PixelRGBValue = [0, 0, 0]
PixelBrightness = 0
PixelOn = False
PixelUpdate = False     #Set to true to indicate that the pixel needs to be updated. Pixel is updated in the main loop.

NewRemoteData = False   #Set to true to indicate that new remote data is available. This is set in the MQTT callbacks, and handled in the main loop.

#A counter that is used to control when the device checks for the time from NTP. By default the device checks
#every ~15 min for NTP if it does not have a valid time, and every 24 hours if it has previously gotten a good time.
NTP_Retry = 0

try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise   #TODO: What does this do?

pixel = neopixel.NeoPixel(board.A0, 1)
wifi.radio.hostname = secrets["device_ID"]

#Set up button interrupts
button_A = countio.Counter(board.D9, edge=countio.Edge.FALL, pull=digitalio.Pull.UP)
button_C = countio.Counter(board.D5, edge=countio.Edge.FALL, pull=digitalio.Pull.UP)

#Initialize variables
LocalData = {
    "temperature":  0,
    "humidity":     0,
    "pressure":     0
}

RemoteData = {
    "temperature":  0,
    "humidity":     0,
    "pressure":     0
}

MQTT_Light_topic = secrets["device_status_topic"] + '#'
MQTT_Remote_Data_Topic = secrets["Remote_Data_Topic"]

MQTT_State_Topic = "homeassistant/sensor/" + secrets["UUID"] + "/state"
MQTT_Config_Temp = "homeassistant/sensor/" + secrets["UUID"]+"_temp/config"
MQTT_Config_Humidity = "homeassistant/sensor/"+secrets["UUID"]+"_humidity/config"
MQTT_Config_Pressure = "homeassistant/sensor/"+secrets["UUID"]+"_pressure/config"

MQTT_lwt = "homeassistant/sensor/"+secrets["UUID"]+"_" + secrets["device_ID"] + "/lwt"

MQTT_Device_info = {"ids":               [secrets["UUID"]],                                         \
                    "name":              secrets["device_name"],                                    \
                    "suggested_area":    "Kitchen",                                                 \
                    "manufacturer":      "Pat Satyshur",                                            \
                    "model":             "Home Assistant Discovery for "+secrets["device_name"],    \
                    "sw_version":        "https://github.com/ilikecake/ESP32-Wall-Display",         \
                    "configuration_url": "https://github.com/ilikecake/ESP32-Wall-Display"          }

MQTT_Config_Temp_Payload = json.dumps({"device_class":           "temperature",                             \
                                       "name":                   secrets["device_name"] + " Temperature",   \
                                       "state_topic":            MQTT_State_Topic,                          \
                                       "unit_of_measurement":    "??F",                                      \
                                       "value_template":         "{{value_json.temperature}}",              \
                                       "unique_id":              secrets["UUID"]+"_temp",                   \
                                       "availability_topic":     MQTT_lwt,                                  \
                                       "payload_available":      "online",                                  \
                                       "payload_not_available":  "offline",                                 \
                                       "device":                 MQTT_Device_info                           })

MQTT_Config_Humidity_Payload = json.dumps({"device_class":           "humidity",                                \
                                           "name":                   secrets["device_name"] + " Humidity",      \
                                           "state_topic":            MQTT_State_Topic,                          \
                                           "unit_of_measurement":    "%",                                       \
                                           "value_template":         "{{value_json.humidity}}",                 \
                                           "unique_id":              secrets["UUID"]+"_humidity",               \
                                           "availability_topic":     MQTT_lwt,                                  \
                                           "payload_available":      "online",                                  \
                                           "payload_not_available":  "offline",                                 \
                                           "device":                 MQTT_Device_info                           })

MQTT_Config_Pressure_Payload = json.dumps({"device_class":           "pressure",                                \
                                           "name":                   secrets["device_name"] + " Pressure",      \
                                           "state_topic":            MQTT_State_Topic,                          \
                                           "unit_of_measurement":    "hPa",                                     \
                                           "value_template":         "{{value_json.pressure}}",                 \
                                           "unique_id":              secrets["UUID"]+"_pressure",               \
                                           "availability_topic":     MQTT_lwt,                                  \
                                           "payload_available":      "online",                                  \
                                           "payload_not_available":  "offline",                                 \
                                           "device":                 MQTT_Device_info                           })



#MQTT Callbacks. Most of these are not used.
def connect(mqtt_client, userdata, flags, rc):
    #This function will be called when the mqtt_client is connected successfully to the broker.
    #print("Connected to MQTT Broker!")
    #print("Flags: {0}\n RC: {1}".format(flags, rc))
    pass

def disconnect(mqtt_client, userdata, rc):
    #This method is called when the mqtt_client disconnects from the broker.
    #print("Disconnected from MQTT Broker!")
    pass

def subscribe(mqtt_client, userdata, topic, granted_qos):
    #This method is called when the mqtt_client subscribes to a new feed.
    #print("Subscribed to {0} with QOS level {1}".format(topic, granted_qos))
    pass

def unsubscribe(mqtt_client, userdata, topic, pid):
    #This method is called when the mqtt_client unsubscribes from a feed.
    #print("Unsubscribed from {0} with PID {1}".format(topic, pid))
    pass

def publish(mqtt_client, userdata, topic, pid):
    #This method is called when the mqtt_client publishes data to a feed.
    #print("Published to {0} with PID {1}".format(topic, pid))
    pass

def message(client, topic, message):
    global RemoteData
    global NewRemoteData
    global PixelRGBValue
    global PixelOn
    global PixelBrightness
    global PixelUpdate
    # Method called when a client's subscribed feed has a new value.
    if topic == MQTT_Remote_Data_Topic:
        #There is new remote data from the server.
        RemoteData = json.loads(message)
        NewRemoteData = True
    elif secrets["device_status_topic"] in topic:
        #This is where we listen for updates to the pixel state from the MQTT server.
        if 'rgb/set' in topic:
            #Set new pixel RGB value
            PixelRGBValue = [int(x) for x in message.split(",")]
            PixelUpdate = True
        elif 'light/switch' in topic:
            #Turn the pixel on or off
            if message == 'ON':
                PixelOn = True
                PixelUpdate = True
            elif message == 'OFF':
                PixelOn = False
                PixelUpdate = True
        elif 'brightness/set' in topic:
            #Set brightness. Brightness should be 0-1
            PixelBrightness = int(message)/256
            PixelUpdate = True

pool = socketpool.SocketPool(wifi.radio)

# Set up a MiniMQTT Client
mqtt_client = MQTT.MQTT(broker=secrets["mqtt_broker_ip"],
                        port=int(secrets["mqtt_broker_port"]),
                        username=secrets["mqtt_broker_user"],
                        password=secrets["mqtt_broker_pass"],
                        socket_pool=pool,
                        ssl_context=ssl.create_default_context(),
                        )

#Connect callback handlers to mqtt_client
mqtt_client.on_connect = connect
mqtt_client.on_disconnect = disconnect
mqtt_client.on_subscribe = subscribe
mqtt_client.on_unsubscribe = unsubscribe
mqtt_client.on_publish = publish
mqtt_client.on_message = message
mqtt_client.will_set(MQTT_lwt,'offline')

def ConnectToNetwork():
    global pixel
    global mqtt_client
    global TheDisplay
    Retries = 0

    TheDisplay.ShowStatus()

    while Retries < TIMEOUT_COUNTS:
        Retries = Retries + 1
        TheDisplay.ClearStatusText()

        if wifi.radio.ipv4_address is None:
            #Not connected to wifi
            print("Connecting to SSID: {0:s}...".format(secrets["ssid"]), end =".")
            TheDisplay.StatusText(1,'Connecting to Wifi')
            TheDisplay.StatusText(2,"SSID: %s" % secrets["ssid"])
            pixel.fill((50, 0, 0))  #Red

            try:
                wifi.radio.connect(secrets["ssid"], secrets["password"])
            except Exception as e:  # pylint: disable=broad-except
                print("Failed ({0:d}/{1:d}). Error: ".format(Retries, TIMEOUT_COUNTS), e)
                TheDisplay.StatusText(3,"Failed ({0:d}/{1:d})".format(Retries, TIMEOUT_COUNTS))
                TheDisplay.StatusText(4,e)
                time.sleep(RETRY_DELAY)
            else:
                if wifi.radio.ipv4_address is not None:
                    print("ok")
                    print("  IP: ", wifi.radio.ipv4_address)
                    Retries = Retries - 1   #Wifi is connected, but MQTT won't try to connect until the next time through the loop.
        else:
            #Connected to wifi, try to connect to MQTT
            print("Connecting to MQTT broker at %s..." % mqtt_client.broker, end =".")
            TheDisplay.StatusText(1,"Connecting to MQTT")
            TheDisplay.StatusText(2,"At: %s" % secrets["mqtt_broker_ip"])
            pixel.fill((0, 0, 50))  #Blue

            try:
                mqtt_client.connect()       #This command has a built in retry/timeout, so it takes about 3 min to fail.
                mqtt_client.subscribe(MQTT_Light_topic, qos=1)
                mqtt_client.subscribe(MQTT_Remote_Data_Topic, qos=1)
                mqtt_client.publish(MQTT_lwt, 'online', qos=1, retain=True)
                mqtt_client.publish(MQTT_Config_Temp, MQTT_Config_Temp_Payload, qos=1, retain=True)
                mqtt_client.publish(MQTT_Config_Humidity, MQTT_Config_Humidity_Payload, qos=1, retain=True)
                mqtt_client.publish(MQTT_Config_Pressure, MQTT_Config_Pressure_Payload, qos=1, retain=True)
            except Exception as e:  # pylint: disable=broad-except
                print("Failed ({0:d}/{1:d}). Error:".format(Retries, TIMEOUT_COUNTS), e)
                TheDisplay.StatusText(3,"Failed ({0:d}/{1:d})".format(Retries, TIMEOUT_COUNTS))
                TheDisplay.StatusText(4,e)
                time.sleep(RETRY_DELAY)     #Note: there is a delay/retry built into the connect function also, so this will take longer than you think.
            else:
                #We are connected to wifi and the MQTT broker.
                pixel.fill((0, 0, 0))  #Off
                print("ok")
                return
    #If we get here, the timeout count is reached. Hard reset the device.
    microcontroller.reset()

#This function has a shorter timeout delay and timeout count than the wifi and MQTT connect functions
# This is because NTP is not required for the device to function, and I don't want the device to stop working if external internet access is lost.
# If this function times out, the device will keep working and periodically check again for NTP access.
# This function will take 5-10 sec to timeout if the NTP servier is not accessable.
# Calling this function with SilentMode = true will not change the display or the pixel. For periodic updates to the time during normal operation, use this mode.
def GetTimeFromNTP(SilentMode = False):
    global pixel
    NTP_Retries = 5
    NTP_Retry_Delay = 1     #sec
    Retries = 0

    if SilentMode == False:
        TheDisplay.ClearStatusText()
        TheDisplay.StatusText(1,"Setting time...")
        TheDisplay.ShowStatus()
        pixel.fill((50, 50, 50))  #White

    print("Setting time...", end =".")

    while True:
        if Retries > NTP_Retries:
            #if we get here, NTP time sync failed
            print("skipped")
            return False
        else:
            Retries = Retries + 1

        try:
            TZ_OFFSET = int(secrets["timezone"]) # time zone offset in hours from UTC
            ntp = adafruit_ntp.NTP(pool, tz_offset=TZ_OFFSET)
            rtc.RTC().datetime = ntp.datetime
        except Exception as e:  # pylint: disable=broad-except
            print("Failed to get time from NTP. Error ({0:d}/{1:d}):".format(Retries, NTP_Retries), e)
            if SilentMode == False:
                TheDisplay.StatusText(2,"Failed ({0:d}/{1:d})".format(Retries, NTP_Retries))
                TheDisplay.StatusText(3,e)
            time.sleep(NTP_Retry_Delay)
        else:
            if SilentMode == False:
                pixel.fill((0, 0, 0))  #Off
            print("ok")
            return True

def GetLocalData():
    #TODO: I2C Error checking goes here...
    #TODO: Type conversion goes here?
    global LocalData

    temp_C = bme280.temperature

    LocalData["temperature"] = (temp_C * 9/5) + 32 #F
    LocalData["humidity"] = bme280.humidity
    LocalData["pressure"] = bme280.pressure

def RemoveMQTT():
    #Sends empty config packets to home assistant. This tells home assistant to delete these sensors from its config.
    #Should never be called, but I am saving this here in case it is needed for debug.
    print("Delete the MQTT sensor")
    mqtt_client.publish(MQTT_Config_Temp, '', qos=1, retain=True)
    mqtt_client.publish(MQTT_Config_Humidity, '', qos=1, retain=True)
    mqtt_client.publish(MQTT_Config_Pressure, '', qos=1, retain=True)

#Initialize I2C and devices
i2c = board.I2C()  # uses board.SCL and board.SDA
TheDisplay = weather_display.WeatherDisplay(i2c)
bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c)

print('')
print("Wall Display ESP32-S3")
print('MAC Address: {0:X}:{1:X}:{2:X}:{3:X}:{4:X}:{5:X}'.format(wifi.radio.mac_address[0],wifi.radio.mac_address[1],wifi.radio.mac_address[2],wifi.radio.mac_address[3],wifi.radio.mac_address[4],wifi.radio.mac_address[5]))

ConnectToNetwork()
NTP_Time_Set = GetTimeFromNTP()
GetLocalData()
TheDisplay.UpdateLocal(LocalData)
mqtt_client.publish(MQTT_State_Topic, json.dumps(LocalData))

now = time.localtime()
OldMin = now.tm_min

TheDisplay.ShowRemote()

while True:
    #Get the time
    now = time.localtime()

    #Handle Neopixel. If new pixel data is recieved from the MQTT broker, the pixel is updated here.
    if PixelUpdate == True:
        print("Update Pixel: PixelOn " + str(PixelOn) + " PixelBrightness: " + str(PixelBrightness) + " PixelRGBValue: " + str(PixelRGBValue))
        if PixelOn:
            pixel.fill(PixelRGBValue)
            pixel.brightness = PixelBrightness
        else:
            pixel.fill((0, 0, 0))
        PixelUpdate = False

    #Handle button presses. Button presses are counted asynchronously. If the count is > 0, the button was pressed.
    #   - If the display is blanked, any button press shows the remote data.
    #   - If the display is showing the remote display, pressing button A will show the local display.
    #   - If the display is showing the local display, pressing button A will show device status.
    #   - If the display is showing the device status, pressing button A will show the local display.
    #   - Pressing button C will always show the remote display.
    if button_A.count > 0:
        print('Button A pressed')
        if TheDisplay.GetDisplayState() == weather_display.DisplayState_Blank:
            TheDisplay.ShowRemote()
        elif TheDisplay.GetDisplayState() == weather_display.DisplayState_Local:
            TheDisplay.ShowStatus()
            print("Show status")
            TheDisplay.StatusText(1, "ESP32-S3 Display")
            TheDisplay.StatusText(2, '{0:X}:{1:X}:{2:X}:{3:X}:{4:X}:{5:X}'.format(wifi.radio.mac_address[0],wifi.radio.mac_address[1],wifi.radio.mac_address[2],wifi.radio.mac_address[3],wifi.radio.mac_address[4],wifi.radio.mac_address[5]))
            TheDisplay.StatusText(3, "SSID: %s" % secrets["ssid"])
            TheDisplay.StatusText(4, "IP: " + str(wifi.radio.ipv4_address))
            TheDisplay.StatusText(5, "MQTT: " + secrets["mqtt_broker_ip"])
        else:
            TheDisplay.ShowLocal()
        button_A.count = 0

    if button_C.count > 0:
        print('Button C pressed')
        if TheDisplay.GetDisplayState() == weather_display.DisplayState_Blank:
            TheDisplay.ShowRemote()
        else:
            TheDisplay.ShowRemote()
        button_C.count = 0

    #Handle the RTC and time setting.
    #   - If we don't have a valid time from NTP, try every ~15 min to get valid data.
    #   - If we have valid time from NTP, try to get an update every ~24 hours.
    #Here we call the GetTimeFromNTP function in 'silent mode' this mode will not change the display.
    #Note that this function may take longer than the tick rate. This will result in skipped ticks when the function runs.
    #The worst case will be if an NTP server is not available. This will cause the device to hang every ~15 min for about
    #10 seconds. The display should be unaffected by this, but if updates to data or button presses will be delayed.
    if ((not NTP_Time_Set) and (NTP_Retry > 500)) or (NTP_Retry > 43200):
        NTP_Time_Set = GetTimeFromNTP(SilentMode = True)
        NTP_Retry = 0
    else:
        NTP_Retry = NTP_Retry + 1

    #Handle MQTT communication. If we get an error sending data, try to reconnect.
    try:
        mqtt_client.loop()
    except (ValueError, RuntimeError, OSError, MQTT.MMQTTException) as e:
        pixel.fill((50, 50, 0)) #yellow
        PixelUpdate = True      #Pixel will need to be updated once this condition is cleared.
        NTP_Retry = 0
        print("Error in MQTT loop: ", e)
        ConnectToNetwork()
        NTP_Time_Set = GetTimeFromNTP()
        TheDisplay.ShowRemote()
        continue

    #Call the display update function. This function will update the display with the latest data and time.
    TheDisplay.Update(now)

    #If we have new data from the remote sensor, pass it to the display class so that it can be shown on the display.
    if NewRemoteData:
        TheDisplay.UpdateRemote(RemoteData)
        NewRemoteData = False

    #Functions that should run on a slower interval. These happen once per minute.
    #   - Get data from the location BMP280 sensor
    #   - Send local data to the display class.
    #   - Print a summary of the local data to the console in case anyone is listening
    #   - Send the local data to the MQTT broker. Try to catch and recover from MQTT errors.
    if now.tm_min != OldMin:
        GetLocalData()
        TheDisplay.UpdateLocal(LocalData)
        print('{0:02d}:{1:02d}:{2:02d}: T:{3:.4f}, P:{4:.4f}, H:{5:.4f}'.format(now.tm_hour,
                                                                                now.tm_min,
                                                                                now.tm_sec,
                                                                                LocalData["temperature"],
                                                                                LocalData["pressure"],
                                                                                LocalData["humidity"]))
        try:
            mqtt_client.publish(MQTT_State_Topic, json.dumps(LocalData))
        except (ValueError, RuntimeError, OSError, MQTT.MMQTTException) as e:
            pixel.fill((50, 50, 0)) #yellow
            PixelUpdate = True      #Pixel will need to be updated once this condition is cleared.
            NTP_Retry = 0
            print("Error sending data: ", e)
            ConnectToNetwork()
            NTP_Time_Set = GetTimeFromNTP()
            continue
        OldMin = now.tm_min

    #This is the primary tick rate of the main loop. This controls how fast everything happens. It is set to run the entire main loop
    #about 5 times per sec. This is probably about as fast as we would need.
    time.sleep(.2)
