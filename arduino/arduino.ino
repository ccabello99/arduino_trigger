#include <Arduino.h>

const int channelPins[] = {2, 3, 4};
const int numChannels = sizeof(channelPins) / sizeof(channelPins[0]);
const int maxEvents = 20; // Maximum number of  events that can be buffered

struct Event {
  unsigned long startTime;
  int channel;
  bool state;
};

Event Events[maxEvents];
int numEvents = 0; // Current number of scheduled  events

void setup() {
  Serial.begin(115200);
  for (int i = 0; i < numChannels; ++i) {
    pinMode(channelPins[i], OUTPUT);
    digitalWrite(channelPins[i], LOW);
  }
}

void sendConfirmation(bool success, String message = "") {
  Serial.print(success ? "Success: " : "Error: ");
  Serial.println(message);
  Serial.flush(); // Ensure message is sent
}

void resetEvents() {
  numEvents = 0; // Clear the  event buffer
}

void scheduleEvent(unsigned long time, int channel, bool state) {
  if (channel < 0 || channel >= numChannels) {
    sendConfirmation(false, "Invalid channel index.");
    return;
  }

  if (numEvents < maxEvents) {
    Events[numEvents].startTime = millis() + time;
    Events[numEvents].channel = channel;
    Events[numEvents].state = state;
    numEvents++;
  } else {
    sendConfirmation(false, "Event buffer full.");
  }
}

void processEvents() {
  unsigned long currentTime = millis();
  for (int i = 0; i < numEvents; ) {
    if ((long)(currentTime - Events[i].startTime) >= 0) {
      digitalWrite(channelPins[Events[i].channel], Events[i].state);
      // Shift remaining events forward
      for (int j = i; j < numEvents - 1; j++) {
        Events[j] = Events[j + 1];
      }
      numEvents--;
    } else {
      i++;
    }
  }
}

void serialFlush() {
  while (Serial.available()) Serial.read();
}

void loop() {
  // Wait for start delimiter
  while (Serial.available() > 0 && Serial.peek() != '<') {
    Serial.read(); // discard until '<'
  }

  if (Serial.available() > 0 && Serial.peek() == '<') {
    Serial.read(); // consume the '<'

    char commandBuffer[512];
    memset(commandBuffer, 0, sizeof(commandBuffer));

    // Read until '>' or buffer full
    int bytesRead = Serial.readBytesUntil('>', commandBuffer, sizeof(commandBuffer) - 1);

    if (bytesRead == 0) {
      sendConfirmation(false, "Empty command.");
      return;
    }

    // ===== Check for STOP command before anything else =====
    if (strncmp(commandBuffer, "STOP;", 5) == 0) {
      // Validate CRC
      int receivedCRC = atoi(commandBuffer + 5);
      int calculatedCRC = 0;
      for (int i = 0; i < 5; ++i) {
        calculatedCRC ^= commandBuffer[i];
      }

    if (calculatedCRC == receivedCRC) {
      resetEvents(); // Clear all scheduled events
      for (int i = 0; i < numChannels; ++i) {
        digitalWrite(channelPins[i], LOW); // Force all outputs LOW
      }
      sendConfirmation(true, "All events cleared and outputs set LOW (STOP).");
    }

      serialFlush();
      return;
    }
    // ===== End of STOP command block =====

    // Normal processing continues here
    // Find last semicolon (which precedes CRC)
    char* lastSemicolon = strrchr(commandBuffer, ';');
    if (lastSemicolon == NULL) {
      sendConfirmation(false, "CRC missing (no semicolon found).");
      return;
    }

    // Extract received CRC string
    char* crcStr = lastSemicolon + 1;
    if (strlen(crcStr) == 0) {
      sendConfirmation(false, "CRC missing (empty after semicolon).");
      return;
    }

    int receivedCRC = atoi(crcStr);

    // Prepare CRC data: everything up to and including last semicolon
    size_t dataLen = lastSemicolon - commandBuffer + 1;
    char crcData[512];
    memset(crcData, 0, sizeof(crcData));
    strncpy(crcData, commandBuffer, dataLen);

    // Compute CRC (XOR)
    int calculatedCRC = 0;
    for (size_t i = 0; i < strlen(crcData); ++i) {
      calculatedCRC ^= crcData[i];
    }

    if (calculatedCRC != receivedCRC) {
      sendConfirmation(false, "CRC mismatch.");
      return;
    }

    resetEvents();

    char* token = strtok(crcData, ";");
    while (token != NULL) {
      int time, channel, state;
      if (sscanf(token, "(%d,%d,%d)", &channel, &time, &state) == 3) {
        scheduleEvent((unsigned long)time, channel, state != 0);
      } else {
        Serial.print("Warning: Skipping invalid token: ");
        Serial.println(token);
      }
      token = strtok(NULL, ";");
    }

    sendConfirmation(true, "Events scheduled.");
    serialFlush();
  }

  // Process events, etc.
  processEvents();
}