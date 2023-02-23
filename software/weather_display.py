
import displayio
import terminalio
from adafruit_display_text import label
import adafruit_displayio_sh1107


_DisplayState_Status = 1
_DisplayState_Remote = 2
_DisplayState_Local = 3
_DisplayState_Blank = 4

class WeatherDisplay:
    def __init__(self, i2c):
        self._display_bus = displayio.I2CDisplay(i2c, device_address=0x3C)
        self._DisplayWidth = 128
        self._DisplayHeight = 64
        self._BorderWidth = 2
        self._display = adafruit_displayio_sh1107.SH1107(self._display_bus, width=self._DisplayWidth, height=self._DisplayHeight, rotation=0)

        self._oldMin = -1
        self._oldDay = -1
        self._DataCounter = 0               #Starts at zero. A zero indicates that no data has been recieved.
        self._DataCounterMax = 100          #Does this need to be a internal variable?
        self._DisplayTimeoutCounter = 0     #
        self._DisplayTimeoutMax = 50       #Does this need to be a internal variable?
        self._LocalDisplayCounter = 0     #
        self._LocalDisplayCounter_Max = 20       #Does this need to be a internal variable?
        self._DisplayIsBlank = True
        self._DisplayState = _DisplayState_Status
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

        #self._display.show(self._BlankDisplay)
        self.Blank()

    def Update(self, now):
        #_DisplayTimeoutCounter: when this reaches zero, blank the display.
        #   Set by: Unblank(), always-on-time
        #
        #_DataCounter: When this reaches zero, the remote data is stale.
        #   Set by: UpdateRemote()
        #print("Disp T/O: " + str(self._DisplayTimeoutCounter) + 
        #      "  Data T/O: " + str(self._DataCounter) + 
        #      "  loc T/O: " + str(self._LocalDisplayCounter) + 
        #      "  blnk: " + str(self._DisplayIsBlank) +
        #      "  state: " + str(self._DisplayState) )
              
        if self._DataCounter > 0:   #TODO: Remote data counter??
            if (self._DataCounter == 1):
                #Remote data lost, switch to status display
                self._DisplayStateChanged = True
                self._RemoteDataLost = True
            elif (self._DataCounter == self._DataCounterMax) and (self._RemoteDataLost == True):
                #When the display is waiting for data, and new data comes in
                #Indicate that the display state needs to be updated here
                self._DisplayStateChanged = True
                self._RemoteDataLost = False
                self.Unblank()
            self._DataCounter = self._DataCounter - 1
        
        if self._DisplayTimeoutCounter > 0:
            if (self._DisplayTimeoutCounter == 1):
                self._DisplayStateChanged = True
            self._DisplayTimeoutCounter = self._DisplayTimeoutCounter - 1
            
        #TODO: This resets the display timeout, do I want that?
        if self._LocalDisplayCounter > 0:
            if (self._LocalDisplayCounter == 1):
                self.ShowRemote()
            self._LocalDisplayCounter = self._LocalDisplayCounter - 1

        if now is not None:
            if now.tm_min != self._oldMin:
                self.UpdateTime(now)
            if now.tm_mday != self._oldDay:
                self.UpdateDate(now)
            if self._DisplayShouldBeOn(now):
                self.Unblank()
                
        

        if self._DisplayStateChanged:
            print("Display State Changed")
            if (self._DisplayTimeoutCounter == 0) and (self._DisplayIsBlank is False):
                print("blank")
                self.Blank()
            else:
                self._DisplayTimeoutCounter = self._DisplayTimeoutMax
                if (self._DisplayState == _DisplayState_Remote):
                    if not self._RemoteDataLost:
                        self._UpdateSensorDisplay()
                        self._display.show(self._WeatherDisplay)
                    else:
                        self.StatusText(1, 'Waiting for data...')
                        self._display.show(self._MessageDisplay)
                elif (self._DisplayState == _DisplayState_Local):
                    self._UpdateSensorDisplay()
                    self._display.show(self._WeatherDisplay)
                elif self._DisplayState == _DisplayState_Status:
                    self._display.show(self._MessageDisplay)
            self._DisplayStateChanged = False

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
        if (self._DisplayState == _DisplayState_Remote):
            self._TempValue.text = "{:.1f}".format(self._RemoteData["temperature"])
            self._HumidityValue.text = "{:.1f}%".format(self._RemoteData["humidity"])
            self._PressureValue.text = "{:.2f}inHg".format(self._RemoteData["pressure"]*0.02953)
        elif (self._DisplayState == _DisplayState_Local):
            self._TempValue.text = "{:.1f}".format(self._LocalData["temperature"])
            self._HumidityValue.text = "{:.1f}%".format(self._LocalData["humidity"])
            self._PressureValue.text = "{:.2f}inHg".format(self._LocalData["pressure"]*0.02953)     #TODO: Make a function to auto-convert?

    def UpdateRemote(self, sensor_data):
        self._DataCounter = self._DataCounterMax
        #self._RemoteDataLost = False
        self._RemoteData = sensor_data
        self._UpdateSensorDisplay()
        
        #TODO: Not sure if this should go here, or in the update function. If I put it here, it is only called when new data exsists.
        #TODO: Maybe make a function that updates the display with new data.
        #if (self._DisplayState == _DisplayState_Remote):
        #    self._TempValue.text = "{:.1f}".format(self._RemoteData["temperature"])
        #    self._HumidityValue.text = "{:.1f}%".format(self._RemoteData["humidity"])
        #    self._PressureValue.text = "{:.2f}inHg".format(self._RemoteData["pressure"]*0.02953)     #TODO: Make a function to auto-convert?

    def UpdateLocal(self, sensor_data):
        #self._DataCounter = self._DataCounterMax   #TODO: Dont reset timeout on local data??
        self._LocalData = sensor_data
        self._UpdateSensorDisplay()
        
        #TODO: Not sure if this should go here, or in the update function. If I put it here, it is only called when new data exsists.
        #if (self._DisplayState == _DisplayState_Local):
        #    self._TempValue.text = "{:.1f}".format(self._LocalData["temperature"])
        #    self._HumidityValue.text = "{:.1f}%".format(self._LocalData["humidity"])
        #    self._PressureValue.text = "{:.2f}inHg".format(self._LocalData["pressure"]*0.02953)     #TODO: Make a function to auto-convert?


    def SetWeatherLabel(self, LabelToSet):
        self._WeatherLabel.text = LabelToSet

    def StatusText(self, LineToDisplay, TextToDisplay):
        if (LineToDisplay > 0) and (LineToDisplay < 6):
            if not isinstance(TextToDisplay, str):
                try:
                    ConvertedText = str(TextToDisplay)
                except: #TODO: I am not supposed to do a catch-all, but I think it makes sense here.
                    ConvertedText = "Can't convert text"   #TODO: make this more descriptive
                self._MessageText[LineToDisplay-1].text = ConvertedText
            else:
                self._MessageText[LineToDisplay-1].text = TextToDisplay

    def ShowStatus(self):
        self.Unblank()
        self._DisplayStateChanged = True
        self._DisplayState = _DisplayState_Status

    def ClearStatusText(self):
        self._MessageText[0].text = ''
        self._MessageText[1].text = ''
        self._MessageText[2].text = ''
        self._MessageText[3].text = ''
        self._MessageText[4].text = ''

    def ShowRemote(self):
        self.Unblank()
        self._DisplayStateChanged = True
        self.SetWeatherLabel("Outside:")
        self._UpdateSensorDisplay()
        self._DisplayState = _DisplayState_Remote
        
    def ShowLocal(self):
        print('Showing local')
        self.Unblank()
        self._DisplayStateChanged = True
        self.SetWeatherLabel("Inside:")
        self._UpdateSensorDisplay()
        self._DisplayState = _DisplayState_Local
        self._LocalDisplayCounter = self._LocalDisplayCounter_Max
        
    def Blank(self):
        self._DisplayIsBlank = True
        self._display.show(self._BlankDisplay)
        
    def Unblank(self):
        if self._DisplayIsBlank:
            self._DisplayIsBlank = False
            self._DisplayStateChanged = True
        self._DisplayTimeoutCounter = self._DisplayTimeoutMax
        
    def DisplayIsBlanked(self):
        return self._DisplayIsBlank

    def _DisplayShouldBeOn(self, now):
        #This function should return true if the display should be always on at this time.
        if (now.tm_hour > 6) and (now.tm_hour < 10):
            return True
        else:
            return False