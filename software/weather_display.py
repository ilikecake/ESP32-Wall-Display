import displayio
import terminalio
from adafruit_display_text import label
import adafruit_displayio_sh1107

DisplayState_Status = 1
DisplayState_Remote = 2
DisplayState_Local = 3
DisplayState_Blank = 4

class WeatherDisplay:
    def __init__(self, i2c):
        self._display_bus = displayio.I2CDisplay(i2c, device_address=0x3C)
        self._DisplayWidth = 128
        self._DisplayHeight = 64
        self._BorderWidth = 2
        self._display = adafruit_displayio_sh1107.SH1107(self._display_bus, width=self._DisplayWidth, height=self._DisplayHeight, rotation=180, brightness=1)

        self._oldMin = -1
        self._oldDay = -1
        
        #These counters are decremented everytime the update function is called.
        self._DataCounter = 0               #Counts down from DataCounterMax to zero. When it reaches zero, connection with the remote sensor is assumed lost.
        self._DisplayTimeoutCounter = 0     #Counts down to zero. Display state is updated when it reaches zero. Initial value can be different for different display states as seen below.
        
        self._DataCounterMax = 500           #Top value for the data counter
        self._RemoteDisplayTimout = 250      #Top value for the display counter when showing the remote sensor data
        self._LocalDisplayTimout = 250       #Top value for the display counter when showing the local sensor data
        self._StatusDisplayTimout = 250      #Top value for the display counter when showing status messages. This value can be overridden by the ShowStatus function.
        
        #Set initial state of the display and data
        self._DisplayState = DisplayState_Status
        self._DisplayStateChanged = False
        self._RemoteDataLost = True

        self._LocalData = {"temperature":  0,
                           "humidity":     0,
                           "pressure":     0 }
                           
        self._RemoteData = {"temperature":  0,
                            "humidity":     0,
                            "pressure":     0 }

        # Make the display groups
        fullscreen_bitmap = displayio.Bitmap(self._DisplayWidth, self._DisplayHeight, 1)
        inner_bitmap = displayio.Bitmap(self._DisplayWidth - self._BorderWidth * 2, self._DisplayHeight - self._BorderWidth * 2, 1)
        color_palette_black = displayio.Palette(1)
        color_palette_black[0] = 0x000000
        color_palette_white = displayio.Palette(1)
        color_palette_white[0] = 0xFFFFFF

        #Blank group
        self._BlankDisplay = displayio.Group()
        blank_sprite = displayio.TileGrid(fullscreen_bitmap, pixel_shader=color_palette_black, x=0, y=0)
        self._BlankDisplay.append(blank_sprite)

        #Message Group
        self._MessageDisplay = displayio.Group()
        #Draw border
        border_sprite_init = displayio.TileGrid(fullscreen_bitmap, pixel_shader=color_palette_white, x=0, y=0)
        inner_sprite_init = displayio.TileGrid(inner_bitmap, pixel_shader=color_palette_black, x=self._BorderWidth, y=self._BorderWidth)
        self._MessageDisplay.append(border_sprite_init)
        self._MessageDisplay.append(inner_sprite_init)
        #Make four lines of text.
        self._MessageText = [label.Label(terminalio.FONT, text=" "*20, color=0xFFFFFF),
                             label.Label(terminalio.FONT, text=" "*20, color=0xFFFFFF),
                             label.Label(terminalio.FONT, text=" "*20, color=0xFFFFFF),
                             label.Label(terminalio.FONT, text=" "*20, color=0xFFFFFF),
                             label.Label(terminalio.FONT, text=" "*20, color=0xFFFFFF)]

        #self._MessageText1 = label.Label(terminalio.FONT, text=" "*20, color=0xFFFFFF)
        self._MessageText[0].anchor_point = (0, 0)
        self._MessageText[0].anchored_position = (self._BorderWidth*2, 1)
        self._MessageDisplay.append(self._MessageText[0])
        #Line 2
        #self._MessageText2 = label.Label(terminalio.FONT, text=" "*20, color=0xFFFFFF)
        self._MessageText[1].anchor_point = (0, 0)
        self._MessageText[1].anchored_position = (self._BorderWidth*2, 11)
        self._MessageDisplay.append(self._MessageText[1])
        #Line 3
        #self._MessageText3 = label.Label(terminalio.FONT, text=" "*20, color=0xFFFFFF)
        self._MessageText[2].anchor_point = (0, 0)
        self._MessageText[2].anchored_position = (self._BorderWidth*2, 22)
        self._MessageDisplay.append(self._MessageText[2])
        #Line 4
        #self._MessageText[3] = label.Label(terminalio.FONT, text=" "*20, color=0xFFFFFF)
        self._MessageText[3].anchor_point = (0, 0)
        self._MessageText[3].anchored_position = (self._BorderWidth*2, 33)
        self._MessageDisplay.append(self._MessageText[3])
        #Line 5
        self._MessageText[4].anchor_point = (0, 0)
        self._MessageText[4].anchored_position = (self._BorderWidth*2, 44)
        self._MessageDisplay.append(self._MessageText[4])

        #Group to display the weather
        self._WeatherDisplay = displayio.Group()
        border_sprite_weather = displayio.TileGrid(fullscreen_bitmap, pixel_shader=color_palette_white, x=0, y=0)
        inner_sprite_weather = displayio.TileGrid(inner_bitmap, pixel_shader=color_palette_black, x=self._BorderWidth, y=self._BorderWidth)
        self._WeatherDisplay.append(border_sprite_weather)
        self._WeatherDisplay.append(inner_sprite_weather)

        line_bitmap = displayio.Bitmap(self._DisplayWidth, 2, 1)
        line_tile = displayio.TileGrid(line_bitmap, pixel_shader=color_palette_white, x=0, y=50)
        self._WeatherDisplay.append(line_tile)

        self._WeatherLabel = label.Label(terminalio.FONT, text=" "*10, color=0xFFFFFF)
        self._WeatherLabel.anchor_point = (0, 0)
        self._WeatherLabel.anchored_position = (self._BorderWidth*2, 1)
        self._WeatherDisplay.append(self._WeatherLabel)

        self._TempValue = label.Label(terminalio.FONT, text=" "*5, scale=2, color=0xFFFFFF)
        self._TempValue.anchor_point = (1.0, 0)
        self._TempValue.anchored_position = (75, 10)
        self._WeatherDisplay.append(self._TempValue)

        temp_unit_text = label.Label(terminalio.FONT, text="F", color=0xFFFFFF)
        temp_unit_text.anchor_point = (0, 0)
        temp_unit_text.anchored_position = (77, 12)
        self._WeatherDisplay.append(temp_unit_text)

        self._HumidityValue = label.Label(terminalio.FONT, text=" "*5, color=0xFFFFFF)
        self._HumidityValue.anchor_point = (1, 0)
        self._HumidityValue.anchored_position = (45, 35)
        self._WeatherDisplay.append(self._HumidityValue)

        self._PressureValue = label.Label(terminalio.FONT, text=" "*9, color=0xFFFFFF)
        self._PressureValue.anchor_point = (1, 0)
        self._PressureValue.anchored_position = (110, 35)
        self._WeatherDisplay.append(self._PressureValue)

        self._TimeDisplay = label.Label(terminalio.FONT, text=" "*8, color=0xFFFFFF)
        self._TimeDisplay.anchor_point = (1.0, 0)
        self._TimeDisplay.anchored_position = (50, 51)
        self._WeatherDisplay.append(self._TimeDisplay)

        self._DateDisplay = label.Label(terminalio.FONT, text=" "*10, color=0xFFFFFF)
        self._DateDisplay.anchor_point = (1.0, 0)
        self._DateDisplay.anchored_position = (126, 51)
        self._WeatherDisplay.append(self._DateDisplay)

        self.Blank()

    def Update(self, now):
        #Display Handling:
        # 'DisplayTimeoutCounter' decrements every time this function is called. When 'DisplayTimeoutCounter' 
        # reaches zero, 'DisplayStateChanged' is set to true and The new desired display state is set in the
        # 'DisplayState' variable. Every time though this function we check if 'DisplayStateChanged'
        # is true, and if so, set the display based on the 'DisplayState' setting. If 'DisplayStateChanged' is
        # false, the display will not update. If the new display state should have a timeout, that should also
        # be set at the same time as 'DisplayStateChanged' is set to true.
        #
        # The 'DataCounter' decrements every time through this loop. 'DataCounter' is reset when new remote data is
        # recieved. If the DataCounter reaches zero, we assume the connection to the remote sensor is lost.
        #
        # The same function that updates the display will handle loss of remote data. If remote data is lost, the
        # remote display will change to say 'Waiting for remote data'. The other screens will be shown as normal.
        
        #print("Display Counter: " + str(self._DisplayTimeoutCounter))

        if self._DataCounter > 0:
            self._DataCounter = self._DataCounter - 1
            if (self._DataCounter == 0):
                #Remote data lost. Note that we don't set a new display state here. If the display state is 'remote' then
                #the display will change to say 'Waiting for data', if another display is showing, it will not change.
                self._DisplayStateChanged = True
                self._RemoteDataLost = True
             
        
        if self._DisplayTimeoutCounter > 0:
            self._DisplayTimeoutCounter = self._DisplayTimeoutCounter - 1
            if (self._DisplayTimeoutCounter == 0):
                #A timeout is reached. Set DisplayStateChanged to true, and set the new display state and timeout.
                self._DisplayStateChanged = True
                if (self._DisplayState == DisplayState_Local) or (self._DisplayState == DisplayState_Status):
                    self._DisplayState = DisplayState_Remote
                    self._DisplayTimeoutCounter = self._RemoteDisplayTimout
                elif self._DisplayState == DisplayState_Remote:
                    #Don't set the timeout counter again here. This makes the display blank until something else wakes it up.
                    self._DisplayState = DisplayState_Blank

        if now is not None:
            if now.tm_min != self._oldMin:
                self.UpdateTime(now)
                self._oldMin = now.tm_min
            if now.tm_mday != self._oldDay:
                self.UpdateDate(now)
                self._oldDay = now.tm_mday
            if self._DisplayShouldBeOn(now):
                #Turn on display
                if self._DisplayState == DisplayState_Blank:
                    self._DisplayStateChanged = True
                    self._DisplayState = DisplayState_Remote

        if self._DisplayStateChanged:
            self._DisplayStateChanged = False
            if self._DisplayState == DisplayState_Remote:
                if self._RemoteDataLost == True:
                    self.StatusText(1, 'Waiting for data...')
                    self._display.show(self._MessageDisplay)
                else:
                    self._UpdateSensorDisplay()
                    self.SetWeatherLabel("Outside:")
                    self._display.show(self._WeatherDisplay)
            elif self._DisplayState == DisplayState_Local:
                self._UpdateSensorDisplay()
                self.SetWeatherLabel("Inside:")
                self._display.show(self._WeatherDisplay)
            elif self._DisplayState == DisplayState_Status:
                self._display.show(self._MessageDisplay)
            elif self._DisplayState == DisplayState_Blank:
                self._display.show(self._BlankDisplay)

    def UpdateTime(self, now):
        if now.tm_hour > 12:
            self._TimeDisplay.text = "{:2}:{:02} PM".format(now.tm_hour-12, now.tm_min)
        elif now.tm_hour == 0:
            self._TimeDisplay.text = "{:2}:{:02} AM".format(12, now.tm_min)
        else:
            self._TimeDisplay.text = "{:2}:{:02} AM".format(now.tm_hour, now.tm_min)

    def UpdateDate(self, now):
        self._DateDisplay.text = "{:2}/{:2}/{:4}".format(now.tm_mon, now.tm_mday, now.tm_year)

    def _UpdateSensorDisplay(self):
        if (self._DisplayState == DisplayState_Remote):
            self._TempValue.text = "{:.1f}".format(self._RemoteData["temperature"])
            self._HumidityValue.text = "{:.1f}%".format(self._RemoteData["humidity"])
            self._PressureValue.text = "{:.2f}inHg".format(self._RemoteData["pressure"]*0.02953)
        elif (self._DisplayState == DisplayState_Local):
            self._TempValue.text = "{:.1f}".format(self._LocalData["temperature"])
            self._HumidityValue.text = "{:.1f}%".format(self._LocalData["humidity"])
            self._PressureValue.text = "{:.2f}inHg".format(self._LocalData["pressure"]*0.02953)     #TODO: Make a function to auto-convert?

    def UpdateRemote(self, sensor_data):
        self._DataCounter = self._DataCounterMax
        self._RemoteData = sensor_data
        self._UpdateSensorDisplay()
        
        if self._RemoteDataLost == True:
            #If we get data again after loosing it, the display will say 'waiting for data'. Setting DisplayStateChanged here to true
            #tells the update function to show the new data.
            self._DisplayStateChanged = True
            self._RemoteDataLost = False
            self.Update(None)

    def UpdateLocal(self, sensor_data):
        #self._DataCounter = self._DataCounterMax   #TODO: Dont reset timeout on local data??
        self._LocalData = sensor_data
        self._UpdateSensorDisplay()

    def SetBrightness(self, BrightnessVal):
        if (BrightnessVal >= 0) and (BrightnessVal <= 1):
            self._display.brightness = BrightnessVal

    def SetWeatherLabel(self, LabelToSet):
        self._WeatherLabel.text = LabelToSet

    def StatusText(self, LineToDisplay, TextToDisplay):
        if (LineToDisplay > 0) and (LineToDisplay < 6):
            if not isinstance(TextToDisplay, str):
                try:
                    ConvertedText = str(TextToDisplay)
                except:
                    ConvertedText = "Can't convert text"
                self._MessageText[LineToDisplay-1].text = ConvertedText
            else:
                self._MessageText[LineToDisplay-1].text = TextToDisplay

    def ShowStatus(self, TimeoutToSet = None):
        #Set TimeoutToSet to 0 to keep the message on the display forever.
        if TimeoutToSet is None:
            TimeoutToSet = self._StatusDisplayTimout
        self._DisplayStateChanged = True
        self._DisplayState = DisplayState_Status
        self._DisplayTimeoutCounter = TimeoutToSet
        self.Update(None)

    def ShowRemote(self):
        #External function to show the remote data.
        print('Showing remote')
        self._DisplayStateChanged = True
        self._DisplayState = DisplayState_Remote
        self._DisplayTimeoutCounter = self._RemoteDisplayTimout
        self.Update(None)
        
    def ShowLocal(self):
        #External function to show the local data.
        print('Showing local')
        self._DisplayStateChanged = True
        self._DisplayState = DisplayState_Local
        self._DisplayTimeoutCounter = self._LocalDisplayTimout
        self.Update(None)
        
    def Blank(self):
        #External function to blank the display.
        self._DisplayStateChanged = True
        self._DisplayState = DisplayState_Blank
        self.Update(None)
    
    def ClearStatusText(self):
        self._MessageText[0].text = ''
        self._MessageText[1].text = ''
        self._MessageText[2].text = ''
        self._MessageText[3].text = ''
        self._MessageText[4].text = ''

    def GetDisplayState(self):
        return self._DisplayState

    def _DisplayShouldBeOn(self, now):
        #This function should return true if the display should be always on at this time.
        if (now.tm_hour > 6) and (now.tm_hour < 10):
            return True
        else:
            return False