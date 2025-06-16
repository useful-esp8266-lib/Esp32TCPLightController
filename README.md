

---

# ESP32 TCP Light Controller

This project provides an example firmware for an ESP32-based device that controls multiple lights (LEDs or relays) over a WiFi TCP connection. The controller is designed to be controlled via simple TCP text commands, making it easy to integrate into home automation setups or control from custom clients (e.g., Python with PyQt UI).

## Features

- Control up to 5 independent lights (GPIO pins configurable)
- TCP server on port 8080 (configurable)
- Supports multiple simultaneous clients (up to 5)
- Simple text command protocol: ON, OFF, TOGGLE, ALL_ON, ALL_OFF, STATUS, LIST, HELP, QUIT
- Detailed serial debugging output
- Easy to extend for more lights or commands

## Hardware Requirements

- ESP32 development board
- LEDs or relay modules connected to GPIO pins (default: 2, 4, 5, 18, 19)
- 3.3V logic compatible devices

## Getting Started

### 1. Flash the Firmware

- Clone or download this repository.
- Open `esp32_tcp_lightcontroller/esp32_tcp_lightcontroller.ino` in Arduino IDE or PlatformIO.
- Update your WiFi credentials in the code:
  ```cpp
  const char* ssid = "YOUR_SSID";
  const char* password = "YOUR_PASSWORD";
  ```
- Select your ESP32 board and flash the firmware.

### 2. Wiring

Connect LEDs or relay modules to the following GPIO pins by default:

| Pin | Label    | Description         |
|-----|----------|---------------------|
| 2   | builtin  | Built-in LED        |
| 4   | light1   | External LED/Relay 1|
| 5   | light2   | External LED/Relay 2|
| 18  | light3   | External LED/Relay 3|
| 19  | light4   | External LED/Relay 4|

You can change the pin assignments in the source code.

### 3. Connect & Control

- Power up the ESP32. It will connect to your WiFi and start a TCP server on port 8080.
- Use any TCP client (e.g., telnet, netcat, or a Python script) to connect:

  ```bash
  telnet <ESP32_IP_ADDRESS> 8080
  ```

- Once connected, you can control the lights using these commands:

  ```
  ON <light_name>     - Turn light on
  OFF <light_name>    - Turn light off
  TOGGLE <light_name> - Toggle light
  STATUS              - Get all lights status
  LIST                - List available lights
  ALL_ON              - Turn all lights on
  ALL_OFF             - Turn all lights off
  HELP                - Show available commands
  QUIT/EXIT           - Disconnect
  ```

#### Example

```
> LIST
  builtin (pin 2)
  light1 (pin 4)
  light2 (pin 5)
  light3 (pin 18)
  light4 (pin 19)

> ON light1
OK: light1 turned ON

> STATUS
  builtin (pin 2): OFF
  light1 (pin 4): ON
  ...
```

## Customization

- **Number of lights:** Edit the `lights[]` array in the `.ino` file.
- **Pin assignment:** Change pin numbers in the `LIGHT_PIN_X` constants.
- **TCP port:** Change `TCP_PORT` in the code.
- **Client limit:** Adjust `MAX_CLIENTS` as needed.

## Python Client Example

You can control the ESP32 from Python. Here’s a simple example:

```python
import socket

HOST = 'ESP32_IP_ADDRESS'
PORT = 8080

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect((HOST, PORT))
    print(s.recv(1024).decode())  # Welcome message
    s.sendall(b'ON light1\n')
    print(s.recv(1024).decode())
```

## License

MIT License

---

## Credits

- [useful-esp8266-lib/Esp32TCPLightController](https://github.com/useful-esp8266-lib/Esp32TCPLightController)
- Inspired by ESP8266/ESP32 DIY IoT automation projects

---

