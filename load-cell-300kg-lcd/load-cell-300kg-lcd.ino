#include <LiquidCrystal.h>
#include "HX711.h"
#define calibration_factor 24452.78 //This value is obtained using the SparkFun_HX711_Calibration sketch
#define DOUT 7   //used to be 3
#define CLK 6    //used to be 2


// initialize the library with the numbers of the interface pins
LiquidCrystal lcd(12, 11, 5, 4, 3, 2);
HX711 scale;
const int tarePin = 8;  //Tare button at pin 8

void setup()
{
  scale.begin(DOUT, CLK);
  scale.set_scale(calibration_factor);

  Serial.begin(115200);

  pinMode(tarePin, INPUT);

  lcd.begin(16, 2);
  // Print a message to the LCD.
  lcd.setCursor(0, 0);
  lcd.print("OLA!");
  delay(1000);
  lcd.setCursor(1, 6);
  lcd.print("kg");

  if(digitalRead(tarePin) == HIGH)
  {
    lcd.setCursor(0,0);
    lcd.print("tare");
    scale.tare();
    delay(500);
  }
}

void loop()
{
  // lcd.setCursor(0, 0);
  // lcd.print(scale.get_units()); //scale.get_units() returns a float
  if (!scale.is_ready())
  {
    return;
  }

  // float weight = scale.get_units(1);
  float weight = scale.get_units(1);

  // lcd.setCursor(0, 0);
  // lcd.print(weight, 2);
  lcd.print(weight);
  // lcd.print(" kg   ");

  Serial.println(weight, 2);
}
