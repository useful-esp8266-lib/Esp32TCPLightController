
/* light controller example using tcp*/
#include <WiFi.h>
#include <WiFiServer.h>
#include <WiFiClient.h>

// WiFi credentials
const char* ssid = "yourssid";
const char* password = "yourpassword";

// TCP Server settings
const int TCP_PORT = 8080;
const int MAX_CLIENTS = 5;
const int BUFFER_SIZE = 256;

// Light control pins
const int LIGHT_PIN_1 = 2;   // Built-in LED
const int LIGHT_PIN_2 = 4;   // External LED/Relay 1
const int LIGHT_PIN_3 = 5;   // External LED/Relay 2
const int LIGHT_PIN_4 = 18;  // External LED/Relay 3
const int LIGHT_PIN_5 = 19;  // External LED/Relay 4

// Light states
struct Light {
  int pin;
  bool state;
  String name;
};

Light lights[] = {
  {LIGHT_PIN_1, false, "builtin"},
  {LIGHT_PIN_2, false, "light1"},
  {LIGHT_PIN_3, false, "light2"},
  {LIGHT_PIN_4, false, "light3"},
  {LIGHT_PIN_5, false, "light4"}
};

const int NUM_LIGHTS = sizeof(lights) / sizeof(lights[0]);

// Global variables
WiFiServer server(TCP_PORT);
WiFiClient clients[MAX_CLIENTS];
bool clientConnected[MAX_CLIENTS];

void setup() {
  Serial.begin(115200);
  delay(1000);
  
  Serial.println("\n=== ESP32 TCP Light Controller ===");
  
  // Initialize light pins
  for (int i = 0; i < NUM_LIGHTS; i++) {
    pinMode(lights[i].pin, OUTPUT);
    digitalWrite(lights[i].pin, LOW);
    Serial.println("Initialized " + lights[i].name + " on pin " + String(lights[i].pin));
  }
  
  // Connect to WiFi
  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi");
  
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  
  Serial.println("\nWiFi connected!");
  Serial.print("IP address: ");
  Serial.println(WiFi.localIP());
  
  // Start TCP server
  server.begin();
  server.setNoDelay(true);
  
  // Initialize client array
  for (int i = 0; i < MAX_CLIENTS; i++) {
    clientConnected[i] = false;
  }
  
  Serial.println("===================================");
  Serial.print("TCP Light Controller listening on port ");
  Serial.println(TCP_PORT);
  Serial.println("Commands:");
  Serial.println("  ON <light_name>   - Turn light on");
  Serial.println("  OFF <light_name>  - Turn light off");
  Serial.println("  TOGGLE <light_name> - Toggle light");
  Serial.println("  STATUS            - Get all light status");
  Serial.println("  LIST              - List available lights");
  Serial.println("  ALL_ON            - Turn all lights on");
  Serial.println("  ALL_OFF           - Turn all lights off");
  Serial.println("===================================");
  
  // Welcome blink
  blinkWelcome();
}

void loop() {
  // Accept new clients
  WiFiClient newClient = server.available();
  if (newClient) {
    handleNewClient(newClient);
  }
  
  // Handle existing clients
  for (int i = 0; i < MAX_CLIENTS; i++) {
    if (clientConnected[i]) {
      if (clients[i].connected()) {
        handleClientData(i);
      } else {
        // Client disconnected
        Serial.println("[DISCONNECT] Client " + String(i) + " from " + 
                       clients[i].remoteIP().toString());
        clients[i].stop();
        clientConnected[i] = false;
      }
    }
  }
  
  delay(10);
}

void handleNewClient(WiFiClient& newClient) {
  // Find available slot
  int clientSlot = -1;
  for (int i = 0; i < MAX_CLIENTS; i++) {
    if (!clientConnected[i]) {
      clientSlot = i;
      break;
    }
  }
  
  if (clientSlot == -1) {
    Serial.println("[REJECT] Max clients reached");
    newClient.println("ERROR: Server full");
    newClient.stop();
    return;
  }
  
  clients[clientSlot] = newClient;
  clientConnected[clientSlot] = true;
  clients[clientSlot].setNoDelay(true);
  
  Serial.println("[CONNECT] Client " + String(clientSlot) + " from " + 
                 newClient.remoteIP().toString() + ":" + String(newClient.remotePort()));
  
  // Send welcome message
  clients[clientSlot].println("=== ESP32 Light Controller ===");
  clients[clientSlot].println("Connected successfully!");
  clients[clientSlot].println("Type 'HELP' for available commands");
  clients[clientSlot].print("> ");
}

void handleClientData(int clientIndex) {
  if (clients[clientIndex].available()) {
    String command = clients[clientIndex].readStringUntil('\n');
    command.trim();
    command.toUpperCase();
    
    if (command.length() > 0) {
      Serial.println("[CMD] Client " + String(clientIndex) + ": " + command);
      processCommand(clientIndex, command);
    }
  }
}

void processCommand(int clientIndex, String command) {
  WiFiClient& client = clients[clientIndex];
  
  if (command == "HELP") {
    sendHelp(clientIndex);
  }
  else if (command == "STATUS") {
    sendStatus(clientIndex);
  }
  else if (command == "LIST") {
    sendLightList(clientIndex);
  }
  else if (command == "ALL_ON") {
    setAllLights(clientIndex, true);
  }
  else if (command == "ALL_OFF") {
    setAllLights(clientIndex, false);
  }
  else if (command.startsWith("ON ")) {
    String lightName = command.substring(3);
    lightName.trim();
    setLight(clientIndex, lightName, true);
  }
  else if (command.startsWith("OFF ")) {
    String lightName = command.substring(4);
    lightName.trim();
    setLight(clientIndex, lightName, false);
  }
  else if (command.startsWith("TOGGLE ")) {
    String lightName = command.substring(7);
    lightName.trim();
    toggleLight(clientIndex, lightName);
  }
  else if (command == "QUIT" || command == "EXIT") {
    client.println("Goodbye!");
    client.stop();
    clientConnected[clientIndex] = false;
    Serial.println("[QUIT] Client " + String(clientIndex) + " disconnected");
    return;
  }
  else {
    client.println("ERROR: Unknown command '" + command + "'");
    client.println("Type 'HELP' for available commands");
  }
  
  client.print("> ");
}

void sendHelp(int clientIndex) {
  WiFiClient& client = clients[clientIndex];
  
  client.println("Available commands:");
  client.println("  ON <light_name>     - Turn light on");
  client.println("  OFF <light_name>    - Turn light off");
  client.println("  TOGGLE <light_name> - Toggle light state");
  client.println("  STATUS              - Show all light status");
  client.println("  LIST                - List available lights");
  client.println("  ALL_ON              - Turn all lights on");
  client.println("  ALL_OFF             - Turn all lights off");
  client.println("  HELP                - Show this help");
  client.println("  QUIT/EXIT           - Disconnect");
  client.println("");
}

void sendStatus(int clientIndex) {
  WiFiClient& client = clients[clientIndex];
  
  client.println("Light Status:");
  client.println("-------------");
  for (int i = 0; i < NUM_LIGHTS; i++) {
    String status = lights[i].state ? "ON " : "OFF";
    client.println("  " + lights[i].name + " (pin " + String(lights[i].pin) + "): " + status);
  }
  client.println("");
}

void sendLightList(int clientIndex) {
  WiFiClient& client = clients[clientIndex];
  
  client.println("Available lights:");
  client.println("-----------------");
  for (int i = 0; i < NUM_LIGHTS; i++) {
    client.println("  " + lights[i].name + " (pin " + String(lights[i].pin) + ")");
  }
  client.println("");
}

void setLight(int clientIndex, String lightName, bool state) {
  WiFiClient& client = clients[clientIndex];
  
  lightName.toLowerCase();
  
  for (int i = 0; i < NUM_LIGHTS; i++) {
    if (lights[i].name == lightName) {
      lights[i].state = state;
      digitalWrite(lights[i].pin, state ? HIGH : LOW);
      
      String stateStr = state ? "ON" : "OFF";
      client.println("OK: " + lights[i].name + " turned " + stateStr);
      Serial.println("[LIGHT] " + lights[i].name + " -> " + stateStr);
      return;
    }
  }
  
  client.println("ERROR: Light '" + lightName + "' not found");
  client.println("Use 'LIST' to see available lights");
}

void toggleLight(int clientIndex, String lightName) {
  WiFiClient& client = clients[clientIndex];
  
  lightName.toLowerCase();
  
  for (int i = 0; i < NUM_LIGHTS; i++) {
    if (lights[i].name == lightName) {
      lights[i].state = !lights[i].state;
      digitalWrite(lights[i].pin, lights[i].state ? HIGH : LOW);
      
      String stateStr = lights[i].state ? "ON" : "OFF";
      client.println("OK: " + lights[i].name + " toggled to " + stateStr);
      Serial.println("[TOGGLE] " + lights[i].name + " -> " + stateStr);
      return;
    }
  }
  
  client.println("ERROR: Light '" + lightName + "' not found");
  client.println("Use 'LIST' to see available lights");
}

void setAllLights(int clientIndex, bool state) {
  WiFiClient& client = clients[clientIndex];
  
  for (int i = 0; i < NUM_LIGHTS; i++) {
    lights[i].state = state;
    digitalWrite(lights[i].pin, state ? HIGH : LOW);
  }
  
  String stateStr = state ? "ON" : "OFF";
  client.println("OK: All lights turned " + stateStr);
  Serial.println("[ALL] All lights -> " + stateStr);
}

void blinkWelcome() {
  Serial.println("Welcome blink sequence...");
  
  // Blink all lights in sequence
  for (int i = 0; i < NUM_LIGHTS; i++) {
    digitalWrite(lights[i].pin, HIGH);
    delay(200);
    digitalWrite(lights[i].pin, LOW);
    delay(100);
  }
  
  // All on, then all off
  for (int i = 0; i < NUM_LIGHTS; i++) {
    digitalWrite(lights[i].pin, HIGH);
  }
  delay(500);
  
  for (int i = 0; i < NUM_LIGHTS; i++) {
    digitalWrite(lights[i].pin, LOW);
  }
  
  Serial.println("Ready for connections!");
}
