

/*
  Hardware connections:
  
  Si7021 -> Teensy 3.5:
  GND -> Teensy GND
  3.3V -> Teensy 3.3V
  SDA -> Teensy 18
  SCL -> Teensy 19

  LED string -> Teensy 3.5:
  D+ -> Teensy 23
  D- -> Teensy GND
  V+ -> barrel jack +
  V- -> barrel jack -

*/

// include libaries necessary for the temp & humidity sensor from Sparkfun
#include <Wire.h>
#include "SparkFun_Si7021_Breakout_Library.h"

// include libraries necessary for controlling the LED matrix
#include <SmartLEDShieldV4.h>  // uncomment this line for SmartLED Shield V4 (needs to be before #include <SmartMatrix3.h>)
#include <SmartMatrix3.h>
#include <FastLED.h>


// setup constants and class instances for LED matrix
#define COLOR_DEPTH 24                  // This sketch and FastLED uses type `rgb24` directly, COLOR_DEPTH must be 24
const uint8_t kMatrixWidth = 32;        // known working: 32, 64, 96, 128
const uint8_t kMatrixHeight = 32;       // known working: 16, 32, 48, 64
const uint8_t kRefreshDepth = 36;       // known working: 24, 36, 48
const uint8_t kDmaBufferRows = 4;       // known working: 2-4, use 2 to save memory, more to keep from dropping frames and automatically lowering refresh rate
const uint8_t kPanelType = SMARTMATRIX_HUB75_32ROW_MOD16SCAN;   // use SMARTMATRIX_HUB75_16ROW_MOD8SCAN for common 16x32 panels
const uint8_t kMatrixOptions = (SMARTMATRIX_OPTIONS_NONE);      // see http://docs.pixelmatix.com/SmartMatrix for options
const uint8_t kBackgroundLayerOptions = (SM_BACKGROUND_OPTIONS_NONE);

SMARTMATRIX_ALLOCATE_BUFFERS(matrix, kMatrixWidth, kMatrixHeight, kRefreshDepth, kDmaBufferRows, kPanelType, kMatrixOptions);
SMARTMATRIX_ALLOCATE_BACKGROUND_LAYER(backgroundLayer, kMatrixWidth, kMatrixHeight, COLOR_DEPTH, kBackgroundLayerOptions);


const int defaultBrightness = 100 * (255 / 100); // full brightness
int centerX = 16;
int centerY = 16;
const rgb24 blankColor = {0, 0, 0};
rgb24 color;
int ledString = 23;

const int camDelay = 5000; // 5s delay to make sure camera has time to take a nice image
// const int scanDelay = 100; // 100 ms delay for scanning function
unsigned long time;
const int DPCdelay = 1000; // one second between switches

char mode[30] = "darkfield"; //leave some extra space in the string for when we change mode later.
int integers[3]; // this will contain integers we send from the main controller.
int circler = 8; // just a starting guess.

// setup class instance for temp and humidity sensor
float humidity = 0;
float tempf = 0;

Weather sensor;

//------------------------------------------------------------------------
void setup() {
  Serial.begin(38400);
  delay(1000);

  // start things up for the temp sensor


  if (sensor.begin() == false) //Begin communication over I2C
  {
    Serial.println("The sensor did not respond. Please check wiring.");
  }

  color.red = 255;
  color.green = 0;
  color.blue = 0;

  // start things up for the LED matrix
  matrix.addLayer(&backgroundLayer);
  matrix.begin();
  const int maxRefreshRate = matrix.getRefreshRate();
  Serial.println("Refresh rate is: ");
  Serial.print(maxRefreshRate);

  backgroundLayer.setBrightness(defaultBrightness);
  pinMode(ledString, OUTPUT);

}
//---------------------------------------------------------------------
void loopCircles(rgb24 backColor, rgb24 frontColor) {
  int circler = 0;
  while (circler < (kMatrixWidth / 2)) {
    unsigned long currentMillis = millis();
    circler += 1;
    drawCleanCircle(backColor, frontColor, circler);
    //now wait a bit to make sure the Pi Camera can take an image
    while (millis() < currentMillis + camDelay);
  }
}
//-----------------------------------------------------------------------
void getWeather()
{
  // Measure Relative Humidity from the HTU21D or Si7021
  humidity = sensor.getRH();

  // Measure Temperature from the HTU21D or Si7021
  tempf = sensor.getTempF();
  // Temperature is measured every time RH is requested.
  // It is faster, therefore, to read it from previous RH
  // measurement with getTemp() instead with readTemp()
}
//-----------------------------------------------------------------------
void drawCleanCircle(rgb24 backColor, rgb24 frontColor, int r) {
  backgroundLayer.fillScreen({0, 0, 0});
  backgroundLayer.fillCircle(centerX, centerY, r+5, backColor);
  backgroundLayer.fillCircle(centerX, centerY, r, frontColor);
  backgroundLayer.swapBuffers();
}
//-----------------------------------------------------------------------
void drawRightSemicircle(rgb24 backColor, rgb24 frontColor, int r) {
  backgroundLayer.fillScreen(backColor);
  backgroundLayer.fillCircle(centerX, centerY, r, frontColor);
  int x0 = centerX + 1;
  int y0 = 0;
  int x1 = kMatrixWidth;
  int y1 = kMatrixHeight;
  backgroundLayer.fillRectangle(x0, y0, x1, y1, backColor);
  backgroundLayer.swapBuffers();
}
//-------------------------------------------------------------------------
void drawLeftSemicircle(rgb24 backColor, rgb24 frontColor, int r) {
  backgroundLayer.fillScreen(backColor);
  backgroundLayer.fillCircle(centerX, centerY, r, frontColor);
  int x0 = 0;
  int y0 = 0;
  int x1 = centerX - 1;
  int y1 = kMatrixHeight;
  backgroundLayer.fillRectangle(x0, y0, x1, y1, backColor);
  backgroundLayer.swapBuffers();
}
//--------------------------------------------------------------------------
void drawLeftSemicircleDark(rgb24 backColor, rgb24 frontColor, int r) {
  backgroundLayer.fillScreen(backColor);
  backgroundLayer.fillCircle(centerX, centerY, r, frontColor);
  int x0 = 0;
  int y0 = 0;
  int x1 = centerX - 1;
  int y1 = kMatrixHeight;
  backgroundLayer.fillRectangle(x0, y0, x1, y1, frontColor);
  backgroundLayer.swapBuffers();
}
//---------------------------------------------------------------------------
void drawRightSemicircleDark(rgb24 backColor, rgb24 frontColor, int r) {
  backgroundLayer.fillScreen(backColor);
  backgroundLayer.fillCircle(centerX, centerY, r, frontColor);
  int x0 = centerX + 1;
  int y0 = 0;
  int x1 = kMatrixWidth;
  int y1 = kMatrixHeight;
  backgroundLayer.fillRectangle(x0, y0, x1, y1, frontColor);
  backgroundLayer.swapBuffers();
}
//----------------------------------------------------------------------------
void scanArray(rgb24 backColor, rgb24 frontColor) {
  unsigned long currentMillis = millis();
  for (int x = 0; x <= kMatrixWidth; x++) {
    for (int y = 0; y <= kMatrixHeight; y++) {
      backgroundLayer.fillScreen(backColor);
      backgroundLayer.drawPixel(x, y, frontColor);
      backgroundLayer.swapBuffers();
      //      while (millis() < currentMillis + scanDelay);
    }
  }
}
//--------------------------------------------------------------------------
void spiral(rgb24 backColor, rgb24 frontColor) {
  int x = 16;
  int y = 16;
  for (int i = 0; i <= kMatrixWidth * kMatrixHeight; i++) {
    backgroundLayer.fillScreen(backColor);
    backgroundLayer.drawPixel(x, y, frontColor);
    backgroundLayer.swapBuffers();
  }
}
//-----------------------------------------------------------------------------
void linescan(rgb24 backColor, rgb24 frontColor, int i, int r) {
    backgroundLayer.fillScreen({0, 0, 0});
    backgroundLayer.fillRectangle(centerX-r, centerY-r, centerX+r, centerY+r, backColor);
    backgroundLayer.drawFastVLine(i, 0, kMatrixHeight, frontColor);
    backgroundLayer.swapBuffers();
}
//-----------------------------------------------------------------------------
void loop() {
  getWeather();
  Serial.print("humidity:");
  // the '0' simply means no decimal points
  Serial.print(humidity, 0);

  Serial.print(",temperature:");
  // the '2' simply means 2 decimal places
  Serial.print(tempf, 2);
  Serial.println();

  char n = '\n';
  char serialdata[30];
  while (Serial.available()) {
    Serial.readBytesUntil(n, serialdata, 30);

    //parse the incoming string
    if (serialdata != NULL) {
      char *strtokIndx = strtok(serialdata, ";");     // get the first part - the string
      strcpy(mode, strtokIndx); // copy it to mode

      int i = 0;
      while (strtokIndx != NULL) {
        strtokIndx = strtok(NULL, ";"); // this continues where the previous call left off
        integers[i] = atoi(strtokIndx);     // convert this part to an integer

        i++;
      }
    }
  }

  if (strncmp(mode, "set_color", 9) == 0) {
    color.red = (uint8_t)integers[0];
    color.green = (uint8_t)integers[1];
    color.blue = (uint8_t)integers[2];
  }

  if (strncmp(mode, "set_center", 10) == 0) {
    centerX = (int)integers[0];
    centerY = (int)integers[1];
  }


  if (strncmp(mode, "solid", 5) == 0) {
    // Completely fill the screen with a single color
    backgroundLayer.fillScreen(blankColor);
    backgroundLayer.fillScreen(color);
    backgroundLayer.swapBuffers();
  }
  else if (strncmp(mode, "calibrate", 9) == 0) {
    // calibrate darkfield/ brightfield
    loopCircles(blankColor, color);
    loopCircles(color, blankColor);
    Serial.println("calibration cycle complete");
  }
  else if (strncmp(mode, "scan", 4) == 0) {
    // scan through all pixels
    scanArray(blankColor, color);
  }
  else if (strncmp(mode, "DPC", 3) == 0) {
    // DPC mode
    unsigned long currentMillis = millis();
    drawRightSemicircle(blankColor, color, circler);
    while (millis() < currentMillis + DPCdelay);
    drawLeftSemicircle(blankColor, color, circler);
    while (millis() < currentMillis + DPCdelay * 2);
  }

  else if (strncmp(mode, "dark_DPC", 8) == 0) {
    unsigned long currentMillis = millis();
    drawRightSemicircleDark(color, blankColor, circler);
    while (millis() < currentMillis + DPCdelay);
    drawLeftSemicircleDark(color, blankColor, circler);
    while (millis() < currentMillis + DPCdelay * 2);
  }
  else if (strncmp(mode, "brightfield", 11) == 0) {
    drawCleanCircle(blankColor, color, circler);
  }
  else if (strncmp(mode, "darkfield", 9) == 0) {
    drawCleanCircle(color, blankColor, circler);
  }
  else if (strncmp(mode, "set_radius", 10) == 0) {
    circler = integers[0];
  }
  else if (strncmp(mode, "linescan_bright", 15) == 0) {
    linescan(color, blankColor, integers[0], circler);
  }
  else if (strncmp(mode, "linescan_dark", 13) == 0) {
    linescan(blankColor, color, integers[0], circler);
  }
  else if (strncmp(mode, "opto", 4) == 0) {
//    analogWrite(ledString, integers[0]);
    if (integers[0] == 1) {
      analogWrite(ledString, 255);
    }
    else if (integers[0] == 0) {
      analogWrite(ledString, 0);
    }
  }
}
