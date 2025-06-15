#include <Arduino.h>

// ========== Config ==========
#define DEBUG 0  // Set to 1 for verbose serial prints

const int channelPins[] = {2, 3, 4};
const int numChannels = sizeof(channelPins) / sizeof(channelPins[0]);
const int maxEvents = 20;

// ========== Data Structures ==========
struct Event {
  unsigned long startTime;  // in micros
  int channel;
  bool state;
};

Event Events[maxEvents];
int numEvents = 0;

// ========== Helpers ==========
void sendConfirmation(bool success, const char* msg = "") {
#if DEBUG
  Serial.print(success ? "OK: " : "ERR: ");
  Serial.println(msg);
#else
  Serial.println(success ? "1" : "0");  // Faster/shorter messages
#endif
}

void resetEvents() {
  numEvents = 0;
#if DEBUG
  Serial.println("Events reset.");
#endif
}

void scheduleEvent(unsigned long delay_us, int channel, bool state) {
  if (channel >= numChannels || channel < 0) {
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
  for (int i = 0; i < numEvents;) {
    if ((long)(now - Events[i].startTime) >= 0) {
      digitalWrite(channelPins[Events[i].channel], Events[i].state);
      Events[i] = Events[--numEvents];  // Fast remove
    } else {
      ++i;
    }
  }
}

// ========== Setup ==========
void setup() {
  Serial.begin(115200);
  pinMode(channelPins[0], OUTPUT);
  pinMode(channelPins[1], OUTPUT);
  pinMode(channelPins[2], OUTPUT);
  digitalWrite(channelPins[0], LOW);
  digitalWrite(channelPins[1], LOW);
  digitalWrite(channelPins[2], LOW);
}

// ========== Main Loop ==========
void loop() {
  // Always process pending events
  processEvents();

  // Wait for start of command
  while (Serial.available() > 0 && Serial.peek() != '<') {
    Serial.read(); // discard garbage
  }

  if (Serial.available() == 0) return;

  if (Serial.read() != '<') return;

  char buffer[512];
  int len = Serial.readBytesUntil('>', buffer, sizeof(buffer) - 1);
  buffer[len] = '\0';

  if (len == 0) {
    sendConfirmation(false, "Empty.");
    return;
  }

  // Handle STOP
  if (strncmp(buffer, "STOP;", 5) == 0) {
    char receivedCRC = atoi(buffer + 5);
    char calcCRC = 0;
    for (int i = 0; i < 5; ++i) calcCRC ^= buffer[i];

    if (calcCRC == receivedCRC) {
      resetEvents();
      for (int i = 0; i < numChannels; ++i) {
        digitalWrite(channelPins[i], LOW);
      }
      sendConfirmation(true, "Stopped.");
    } else {
      sendConfirmation(false, "Bad CRC.");
    }
    while (Serial.available()) Serial.read();
    return;
  }

  // Handle event commands
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

  char calcCRC = 0;
  for (size_t i = 0; i < dataLen; ++i) {
    calcCRC ^= data[i];
  }

  if (calcCRC != receivedCRC) {
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
    }
#if DEBUG
    else {
      Serial.print("Skip: ");
      Serial.println(token);
    }
#endif
    token = strtok(NULL, ";");
  }

  sendConfirmation(true, "Scheduled.");
  while (Serial.available()) Serial.read();
}
