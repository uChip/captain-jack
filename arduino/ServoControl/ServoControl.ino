
/*
  Reads an incoming text stream and parses to control servos.
  Extracts key characters followed by integers (integer strings terminated by any non-numeric character):
    b<BB>  BB = multi-character integer in the range of 0 to 45
    p<PP>  PP = multi-character integer in the range of 0 to 60
    r<RR>  RR = multi-character integer in the range of 0 to 60
    y<YY>  YY = multi-character integer in the range of 0 to 90

  after receiving b, the angle value is limit checked then sent to the servo subroutine immediately.
  after receiving p,r,y or t, local variables are limit checked and saved.
  after receiving s, a servo ease command is sent and all three servos are started.
  all other characters ignored, including numeric characters not immediately following b, p, r, y or t.

*/

#include <Arduino.h>
#include <Servo.h>

#define ENABLE_EASE_CUBIC
#include "ServoEasing.hpp"

// --- PIN CONFIGURATION ---
const uint8_t JOYSTICK_ROLL_PIN = A0;
const uint8_t JOYSTICK_PITCH_PIN = A1;
const uint8_t JOYSTICK_YAW_PIN = A2;

const uint8_t SERVO_PITCH_PIN = 3;
const uint8_t SERVO_ROLL_PIN = 5;
const uint8_t SERVO_YAW_PIN = 6;
const uint8_t SERVO_BEAK_PIN = 11;
const uint8_t SERVO_PWR_ENBL = 13;

// --- BEAK SERVO CONFIGURATION ---
const int BEAK_CLOSED = 80;
const int BEAK_OPEN = 125;

// --- HEAD SERVOS CONFIGURATION ---
const int PITCH_MID = 90;   // Adjust to center
const int ROLL_MID = 90;    // Adjust to center
const int YAW_MID = 90;     // Adjust to center
const int PITCH_MAX = 120;  // Adjust to travel limit
const int ROLL_MAX = 120;   // Adjust to travel limit
const int YAW_MAX = 135;    // Adjust to travel limit
const int PITCH_MIN = 60;   // Adjust to travel limit
const int ROLL_MIN = 60;    // Adjust to travel limit
const int YAW_MIN = 45;     // Adjust to travel limit

ServoEasing beakServo;
ServoEasing pitchServo;
ServoEasing rollServo;
ServoEasing yawServo;

#define DEBUG
//#define SERVO

void setup() {
  Serial.begin(115200);
#if defined(DEBUG)
  Serial.println(F("Just a message at the beginning."));
#endif

  //Enable servo power
  pinMode(SERVO_PWR_ENBL, OUTPUT);
  digitalWrite(SERVO_PWR_ENBL, HIGH);  // Enable servo power

  //Initialize servos
  beakServo.attach(SERVO_BEAK_PIN);
  beakServo.write(BEAK_CLOSED);
  pitchServo.attach(SERVO_PITCH_PIN);
  pitchServo.write(PITCH_MID);
  rollServo.attach(SERVO_ROLL_PIN);
  rollServo.write(ROLL_MID);
  yawServo.attach(SERVO_YAW_PIN);
  yawServo.write(YAW_MID);

  /* DDEBUG
  delay(500);
  Serial.println(F("Beak open."));
  beakServo.write((int)BEAK_OPENED);
  delay(500);
  Serial.println(F("Beak close."));
  beakServo.write((int)BEAK_CLOSED);
  delay(500);
  Serial.println(F("Beak open."));
  beakServo.write((int)BEAK_OPENED);
  delay(500);
  Serial.println(F("Beak close."));
  beakServo.write((int)BEAK_CLOSED);
  delay(500);
  */
}

uint8_t beakAngle = BEAK_CLOSED;
uint8_t pitchAngle = PITCH_MID;
uint8_t rollAngle = ROLL_MID;
uint8_t yawAngle = YAW_MID;
long duration = 100;

void loop() {
  if (Serial.available() > 0) {  // Data is available to read
    char incomingByte = Serial.read();
#if defined(DEBUG)
    Serial.print(incomingByte);
#endif

    if (incomingByte == 'b') {
      beakAngle = Serial.parseInt();  // Note: values over 255 will wrap (only lowest byte is used)
      if ((beakAngle += BEAK_CLOSED) > BEAK_OPEN) beakAngle = BEAK_OPEN; // Could remove bounds check from library since we do it here more efficiently (only need to check one end)
#if defined(SERVO)
      beakServo.write((uint8_t)beakAngle);
#endif
#if defined(DEBUG)
      Serial.println(beakAngle);
#endif

    } else if (incomingByte == 'p') {
      pitchAngle = Serial.parseInt();
      if ((pitchAngle += PITCH_MIN) > PITCH_MAX) pitchAngle = PITCH_MAX;
#if defined(DEBUG)
      Serial.print(pitchAngle);
#endif

    } else if (incomingByte == 'r') {
      rollAngle = Serial.parseInt();
      if ((rollAngle += ROLL_MIN) > ROLL_MAX) rollAngle = ROLL_MAX;
      rollServo.setEaseTo((int)rollAngle);
#if defined(DEBUG)
      Serial.print(rollAngle);
#endif

    } else if (incomingByte == 'y') {
      yawAngle = Serial.parseInt();
      if ((yawAngle += YAW_MIN) > YAW_MAX) yawAngle = YAW_MAX;
#if defined(DEBUG)
      Serial.print(yawAngle);
#endif

    } else if (incomingByte == 't') {
      duration = Serial.parseInt();
#if defined(DEBUG)
      Serial.print(duration);
#endif

    } else if (incomingByte == 's') {
      pitchServo.setEaseTo(pitchAngle);  // Hmmm, what happens when setEaseTo is sent before current easeTo is finished?
      rollServo.setEaseTo(rollAngle);
      yawServo.setEaseTo(yawAngle);
      setEaseToDForAllServos(duration);
#if defined(SERVO)
      synchronizeAllServosAndStartInterrupt();
#endif
#if defined(DEBUG)
      Serial.print('\n');
      Serial.print('p');
      Serial.print(pitchAngle);
      Serial.print('r');
      Serial.print(rollAngle);
      Serial.print('y');
      Serial.print(yawAngle);
      Serial.print('t');
      Serial.print(duration);
      Serial.println("Start!");
#endif

    } else {
      //Serial.read();  // throw away anything else
    }
  }
}
