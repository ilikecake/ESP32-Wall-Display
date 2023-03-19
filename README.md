# ESP32 Wall Display

This project is a small wall display that shows temperature, humidity and barometric pressure from a remote sensor. The display and sensor communicate over MQTT using [Home Assistant](https://www.home-assistant.io/) as a backend. The display is housed in a 3D printed case and takes 5V DC power. This display is designed to work with my [weather station](https://github.com/ilikecake/ESP32-Weather-Station), but can be easily adapter to other sensors if desired.

[<img src="https://github.com/ilikecake/ESP32-Wall-Display/blob/main/assets/overview_assembled.jpg" height="200">](https://raw.githubusercontent.com/ilikecake/ESP32-Wall-Display/main/assets/overview_assembled.jpg)

Features
* Small OLED display (~1.3" diagonal)
* Two buttons to toggle through displays. Can be adapted to other functions if desired.
* RGB LED can be set by Home Assistant over MQTT to notify the user.
* Measures local temperature, humidity, barometric pressure using a BME280 sensor.
* 3D printed case.
* Powered by 5V (standard USB power supplies will work)
* Wifi connectivity from ESP32.

Building this project will require:
* 3D printer to print the case components.
* Basic soldering capability for the wiring.

For information on how to build this project, see the wiki.
