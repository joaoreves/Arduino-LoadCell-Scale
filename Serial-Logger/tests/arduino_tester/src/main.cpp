#include <Arduino.h>
#include <math.h>

const unsigned long READING_INTERVAL_MS = 100;
const unsigned long WAVE_PERIOD_MS = 8000;
const float CENTER_WEIGHT_KG = 100.0f;
const float AMPLITUDE_KG = 50.0f;

unsigned long lastReadingAt = 0;

void setup()
{
  Serial.begin(115200);
}

void loop()
{
  const unsigned long now = millis();
  if (now - lastReadingAt < READING_INTERVAL_MS)
  {
    return;
  }
  lastReadingAt = now;

  const float phase = 2.0f * PI * (now % WAVE_PERIOD_MS) / WAVE_PERIOD_MS;
  const float simulatedWeight = CENTER_WEIGHT_KG + AMPLITUDE_KG * sin(phase);
  Serial.println(simulatedWeight, 2);
}
