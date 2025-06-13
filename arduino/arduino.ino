#include <Arduino.h>

const int channelPins[] = {2, 3, 4};
const int numChannels = sizeof(channelPins) / sizeof(channelPins[0]);
const int maxEvents = 20;

struct Event {
  unsigned long startTime;  // in micros
  int channel;
  bool state;
};

Event Events[maxEvents];
int numEvents = 0;

void setup() {
  Serial.begin(115200);
  for (int i = 0; i < numChannels; ++i) {
    pinMode(channelPins[i], OUTPUT);
    digitalWrite(channelPins[i], LOW);
  }
}

void sendConfirmation(bool success, const char* message = "") {
  Serial.print(success ? "OK: " : "ERR: ");
  Serial.println(message);
}

void resetEvents() {
  numEvents = 0;
}

void scheduleEvent(unsigned long delay_us, int channel, bool state) {
  if (channel < 0 || channel >= numChannels) {
    sendConfirmation(false, "Bad channel.");
    return;
  }

  if (numEvents < maxEvents) {
    Events[numEvents++] = {micros() + delay_us, channel, state};
  } else {
    sendConfirmation(false, "Event buffer full.");
  }
}

void processEvents() {
  unsigned long now = micros();
  for (int i = 0; i < numEvents; ) {
    if ((long)(now - Events[i].startTime) >= 0) {
      digitalWrite(channelPins[Events[i].channel], Events[i].state);
      Events[i] = Events[--numEvents];  // Fast remove
    } else {
      ++i;
    }
  }
}

void serialFlushInput() {
  while (Serial.available()) Serial.read();
}

void loop() {
  while (Serial.available() > 0 && Serial.peek() != '<') {
    Serial.read();
  }

  if (Serial.available() > 0 && Serial.peek() == '<') {
    Serial.read();  // consume '<'

    char buffer[512];
    int len = Serial.readBytesUntil('>', buffer, sizeof(buffer) - 1);
    buffer[len] = '\0';

    if (len == 0) {
      sendConfirmation(false, "Empty.");
      return;
    }

    // Handle STOP command
    if (strncmp(buffer, "STOP;", 5) == 0) {
      int receivedCRC = atoi(buffer + 5);
      int crc = 0;
      for (int i = 0; i < 5; ++i) crc ^= buffer[i];

      if (crc == receivedCRC) {
        resetEvents();
        for (int i = 0; i < numChannels; ++i) {
          digitalWrite(channelPins[i], LOW);
        }
        sendConfirmation(true, "Stopped.");
      } else {
        sendConfirmation(false, "Bad CRC.");
      }
      serialFlushInput();
      return;
    }

    // Regular event parsing
    char* lastSemi = strrchr(buffer, ';');
    if (!lastSemi || *(lastSemi + 1) == '\0') {
      sendConfirmation(false, "No CRC.");
      return;
    }

    int receivedCRC = atoi(lastSemi + 1);
    size_t dataLen = lastSemi - buffer + 1;
    char data[512];
    strncpy(data, buffer, dataLen);
    data[dataLen] = '\0';

    int crc = 0;
    for (size_t i = 0; i < dataLen; ++i) {
      crc ^= data[i];
    }

    if (crc != receivedCRC) {
      sendConfirmation(false, "CRC mismatch.");
      return;
    }

    resetEvents();

    char* token = strtok(data, ";");
    while (token != NULL) {
      char* p1 = strchr(token, '(');
      char* c1 = strchr(p1, ',');
      char* c2 = strchr(c1 + 1, ',');
      char* p2 = strchr(c2 + 1, ')');

      if (p1 && c1 && c2 && p2) {
        *c1 = *c2 = *p2 = '\0';
        int ch = atoi(p1 + 1);
        int time = atoi(c1 + 1);
        int state = atoi(c2 + 1);
        scheduleEvent((unsigned long)time * 1000, ch, state != 0);
      } else {
        Serial.print("Skip: ");
        Serial.println(token);
      }

      token = strtok(NULL, ";");
    }

    sendConfirmation(true, "Scheduled.");
    serialFlushInput();
  }

  processEvents();
}