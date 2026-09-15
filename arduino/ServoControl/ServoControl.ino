
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
const int BEAK_OPENED = 125;

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


void setup() {
  Serial.begin(115200);
  //Serial.println(F("Just a message at the beginning."));

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

void loop() {
  if (Serial.available() > 0) {  // Data is available to read
    char incomingByte = Serial.read();
    Serial.print(incomingByte);

    if (incomingByte == 'b') {
      long beakAngle = Serial.parseInt();
      beakServo.write((int)beakAngle + BEAK_CLOSED);
      Serial.print(beakAngle);
    } else if (incomingByte == 'p') {
      long pitchAngle = Serial.parseInt();
      pitchServo.setEaseTo((int)pitchAngle + PITCH_MIN);
      Serial.print(pitchAngle);
    } else if (incomingByte == 'r') {
      long rollAngle = Serial.parseInt();
      rollServo.setEaseTo((int)rollAngle + ROLL_MIN);
      Serial.print(rollAngle);
    } else if (incomingByte == 'y') {
      long yawAngle = Serial.parseInt();
      yawServo.setEaseTo((int)yawAngle + YAW_MIN);
      Serial.print(yawAngle);
    } else if (incomingByte == 't') {
      long duration = Serial.parseInt();
      setEaseToDForAllServos(duration);
      Serial.print(duration);
    } else if (incomingByte = '\n') {
      //synchronizeAllServosAndStartInterrupt();
      Serial.println();
    } else {
      Serial.read();  // throw away anything else
    }
  }
}
