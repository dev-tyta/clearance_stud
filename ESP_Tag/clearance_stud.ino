// esp32_nfc_clearance.ino - FIXED VERSION
#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <SPI.h>
#include <MFRC522.h>
#include <WiFiClientSecure.h>

// --- Configuration ---

// WiFi credentials
const char* ssid = "Yess";
const char* password = "hardeykoryar7";

// FastAPI server configuration
const char* serverUrl = "https://didactic-space-computing-machine-x4wwjxjv9wrc6vr-8000.app.github.dev";
String deviceId = ""; // Will be generated from hardware
const char* deviceLocation = "ELE Department";
String apiKey = "";

// MFRC522 RFID module pins
#define SS_PIN 4
#define RST_PIN 22
MFRC522 rfid(SS_PIN, RST_PIN);

// --- State Variables ---
String lastTagId = "";
unsigned long lastScanTime = 0;
const unsigned long scanCooldown = 3000;

struct StudentData {
    String studentId;
    String name;
    bool overallStatus;
};

StudentData currentStudent;

// --- Function Prototypes ---
void connectToWiFi();
void registerDevice();
String getTagId();
void submitTagForLinking(String tagId);
String generateDeviceId();
void initializeDeviceId();

// --- Setup ---
void setup() {
    Serial.begin(115200);
    Serial.println("ESP32 NFC Clearance Reader - Initializing...");

    // Generate unique device ID from hardware
    initializeDeviceId();

    // Initialize RFID reader
    SPI.begin();
    rfid.PCD_Init();
    Serial.println("RFID Reader initialized");

    // Connect to WiFi
    connectToWiFi();
    
    Serial.println("Ready to scan. Hold a tag near the reader.");
}

// --- Main Loop ---
void loop() {
    unsigned long currentTime = millis();

    // Check WiFi connection
    if (WiFi.status() != WL_CONNECTED) {
        Serial.println("WiFi Disconnected. Attempting to reconnect...");
        connectToWiFi();
        delay(1000);
        return;
    }

    // Register device if not already registered
    if (apiKey.length() == 0) {
        registerDevice();
        if (apiKey.length() == 0) {
            Serial.println("Device registration failed. Retrying in 5 seconds...");
            delay(5000);
            return;
        }
    }

    // Check for RFID tags (with cooldown)
    if ((currentTime - lastScanTime) > scanCooldown) {
        if (rfid.PICC_IsNewCardPresent() && rfid.PICC_ReadCardSerial()) {
            String tagId = getTagId();
            Serial.println("Tag detected: " + tagId);
            
            submitTagForLinking(tagId);
            
            lastScanTime = currentTime;
            lastTagId = tagId;

            rfid.PICC_HaltA();
            rfid.PCD_StopCrypto1();
        }
    }

    delay(100); // Small delay for stability
}

// --- Helper Functions ---

void connectToWiFi() {
    if (WiFi.status() == WL_CONNECTED) {
        return;
    }

    Serial.print("Connecting to WiFi");
    WiFi.begin(ssid, password);
    
    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < 20) {
        delay(500);
        Serial.print(".");
        attempts++;
    }
    
    if (WiFi.status() == WL_CONNECTED) {
        Serial.println();
        Serial.println("WiFi connected!");
        Serial.print("IP address: ");
        Serial.println(WiFi.localIP());
    } else {
        Serial.println();
        Serial.println("WiFi connection failed!");
    }
}

void registerDevice() {
    if (WiFi.status() != WL_CONNECTED) {
        Serial.println("WiFi not connected, cannot register device.");
        return;
    }

    Serial.println("Registering device...");

    HTTPClient http;
    WiFiClientSecure client;
    
    // For GitHub Codespaces, we can skip certificate verification
    client.setInsecure(); // This allows connection without certificate verification
    
    String registrationUrl = String(serverUrl) + "/api/devices/register";
    Serial.println("Registration URL: " + registrationUrl);

    if (!http.begin(client, registrationUrl)) {
        Serial.println("Failed to begin HTTP connection for registration.");
        return;
    }

    http.addHeader("Content-Type", "application/json");
    http.setTimeout(10000); // 10 second timeout

    // Create JSON payload
    DynamicJsonDocument doc(512);
    doc["device_id"] = deviceId;
    doc["location"] = deviceLocation;

    String payload;
    serializeJson(doc, payload);

    Serial.println("Registration payload: " + payload);

    int httpResponseCode = http.POST(payload);
    
    Serial.println("HTTP Response Code: " + String(httpResponseCode));

    if (httpResponseCode > 0) {
        String response = http.getString();
        Serial.println("Registration response: " + response);

        if (httpResponseCode == 200 || httpResponseCode == 201) {
            // Parse response to get API key
            DynamicJsonDocument respDoc(1024);
            DeserializationError error = deserializeJson(respDoc, response);

            if (!error && respDoc.containsKey("api_key")) {
                apiKey = respDoc["api_key"].as<String>();
                Serial.println("Device registered successfully!");
                Serial.println("API Key: " + apiKey);
            } else {
                Serial.println("Error parsing registration response or missing API key");
                Serial.println("Parse error: " + String(error.c_str()));
            }
        } else {
            Serial.println("Registration failed with HTTP code: " + String(httpResponseCode));
        }
    } else {
        Serial.println("HTTP request failed: " + http.errorToString(httpResponseCode));
    }

    http.end();
}

void submitTagForLinking(String tagId) {
    if (WiFi.status() != WL_CONNECTED) {
        Serial.println("WiFi not connected, cannot submit tag.");
        return;
    }
    
    if (apiKey.length() == 0) {
        Serial.println("No API key, cannot submit tag.");
        return;
    }

    Serial.println("Submitting tag for linking: " + tagId);

    HTTPClient http;
    WiFiClientSecure client;
    
    // Skip certificate verification for GitHub Codespaces
    client.setInsecure();

    String endpoint = String(serverUrl) + "/api/devices/submit-scanned-tag";
    Serial.println("Endpoint: " + endpoint);

    if (!http.begin(client, endpoint)) {
        Serial.println("Failed to begin HTTP connection for tag submission.");
        return;
    }

    http.addHeader("Content-Type", "application/json");
    http.addHeader("X-API-KEY", apiKey);
    http.setTimeout(10000); // 10 second timeout

    // Create JSON payload
    DynamicJsonDocument doc(256);
    doc["scanned_tag_id"] = tagId;

    String payload;
    serializeJson(doc, payload);

    Serial.println("Tag submission payload: " + payload);

    int httpResponseCode = http.POST(payload);
    
    Serial.println("HTTP Response Code: " + String(httpResponseCode));

    if (httpResponseCode > 0) {
        String response = http.getString();
        Serial.println("Tag submission response: " + response);

        switch (httpResponseCode) {
            case 200:
                Serial.println("✓ Tag submitted successfully for linking!");
                break;
            case 202:
                Serial.println("✓ Tag submission accepted, pending processing.");
                break;
            case 400:
                Serial.println("✗ Bad Request - Check tag format or no pending link.");
                break;
            case 401:
                Serial.println("✗ Authentication failed - clearing API key for re-registration.");
                apiKey = "";
                break;
            case 404:
                Serial.println("✗ Endpoint not found or resource not found.");
                break;
            case 409:
                Serial.println("✗ Conflict - Tag may already be linked.");
                break;
            default:
                Serial.println("✗ Unexpected server response: " + String(httpResponseCode));
                break;
        }
    } else {
        Serial.println("HTTP request failed: " + http.errorToString(httpResponseCode));
        
        // Check specific error conditions
        if (httpResponseCode == HTTPC_ERROR_CONNECTION_REFUSED) {
            Serial.println("Connection refused - server may be down or URL incorrect.");
        } else if (httpResponseCode == HTTPC_ERROR_CONNECTION_LOST) {
            Serial.println("Connection lost during request.");
        } else if (httpResponseCode == HTTPC_ERROR_NO_HTTP_SERVER) {
            Serial.println("No HTTP server found at the specified URL.");
        }
    }

    http.end();
}

String getTagId() {
    String tagId = "";
    for (byte i = 0; i < rfid.uid.size; i++) {
        if (rfid.uid.uidByte[i] < 0x10) {
            tagId += "0";
        }
        tagId += String(rfid.uid.uidByte[i], HEX);
    }
    tagId.toUpperCase();
    return tagId;
}

// Generate unique device ID from ESP32 hardware
void initializeDeviceId() {
    deviceId = generateDeviceId();
    Serial.println("Device ID: " + deviceId);
}

String generateDeviceId() {
    // Option 1: Use ESP32 MAC Address (most common and reliable)
    // uint8_t mac[6];
    // WiFi.macAddress(mac);
    // String macId = "ESP32_";
    // for (int i = 0; i < 6; i++) {
    //     if (mac[i] < 0x10) macId += "0";
    //     macId += String(mac[i], HEX);
    // }
    // macId.toUpperCase();
    // return macId;
    
    // /* Alternative Options (uncomment to use):
    
    // // Option 2: Use ESP32 Chip ID (unique 48-bit identifier)
    // uint64_t chipId = ESP.getEfuseMac();
    // String chipIdStr = "ESP32_CHIP_" + String((uint32_t)(chipId >> 32), HEX) + String((uint32_t)chipId, HEX);
    // chipIdStr.toUpperCase();
    // return chipIdStr;
    
    // Option 3: Use MFRC522 Version (less unique, not recommended)
    byte version = rfid.PCD_ReadRegister(rfid.VersionReg);
    String rfidId = "ESP32_RFID_" + String(version, HEX) + "_" + String(random(1000, 9999));
    rfidId.toUpperCase();
    return rfidId;
    
    // // Option 4: Combined approach for maximum uniqueness
    // uint8_t mac[6];
    // WiFi.macAddress(mac);
    // uint64_t chipId = ESP.getEfuseMac();
    // String combinedId = "ESP32_";
    // for (int i = 3; i < 6; i++) { // Use last 3 bytes of MAC
    //     if (mac[i] < 0x10) combinedId += "0";
    //     combinedId += String(mac[i], HEX);
    // }
    // combinedId += "_" + String((uint32_t)chipId, HEX);
    // combinedId.toUpperCase();
    // return combinedId;
    // // */
}